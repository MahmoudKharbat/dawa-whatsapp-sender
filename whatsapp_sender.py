"""
WhatsApp Sending Logic with Selenium
Handles bulk message sending in a single tab with persistent login.
"""

import logging
import os
import random
import re
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any, Callable, List, Optional

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from config import (
    MAX_DELAY,
    MIN_DELAY,
    WHATSAPP_CHAT_NAV_PAUSE_SEC,
    WHATSAPP_COMPOSER_WAIT_SEC,
    WHATSAPP_IMAGE_PREVIEW_WAIT_SEC,
    WHATSAPP_INITIAL_PAGE_PAUSE_SEC,
    WHATSAPP_LOGIN_TIMEOUT_SEC,
    WHATSAPP_MEDIA_POST_CLEAR_HOLD_SEC,
    WHATSAPP_MEDIA_SEND_CONFIRM_TIMEOUT_SEC,
)

logger = logging.getLogger(__name__)


class WhatsAppSender:
    """Handles WhatsApp message sending using a single Selenium browser instance."""

    def __init__(self, on_progress: Optional[Callable] = None, on_complete: Optional[Callable] = None):
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.is_sending = False
        self.sender_thread = None
        self._driver: Optional[webdriver.Chrome] = None
        self._driver_lock = threading.Lock()

    def send_messages(
        self,
        phone_numbers: List[str],
        message: str,
        image_path: Optional[str] = None,
    ) -> None:
        """Start sending WhatsApp messages (text and/or image) in a separate thread."""
        has_text = bool(message and message.strip())
        has_image = bool(image_path and Path(image_path).is_file())

        if not phone_numbers:
            logger.warning("No phone numbers")
            if self.on_complete:
                self.on_complete(0, 0, ["No phone numbers"])
            return

        if not has_text and not has_image:
            logger.warning("Empty message and no image")
            if self.on_complete:
                self.on_complete(0, 0, ["Empty message and no image selected"])
            return

        if self.is_sending:
            logger.warning("Already sending messages")
            return

        self.is_sending = True
        self.sender_thread = threading.Thread(
            target=self._send_messages_worker,
            args=(phone_numbers, message or "", image_path),
            daemon=True,
        )
        self.sender_thread.start()

    def shutdown_browser(self) -> None:
        """Close the Chrome session (call when exiting the app). Sending leaves the browser open."""
        with self._driver_lock:
            if self._driver is not None:
                try:
                    self._driver.quit()
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
                self._driver = None

    def _create_fresh_driver(self) -> webdriver.Chrome:
        """Start Chrome with persistent profile and wait until WhatsApp main UI is ready."""
        chrome_options = Options()
        user_data_dir = os.path.join(os.getcwd(), "whatsapp_session")
        chrome_options.add_argument(f"user-data-dir={user_data_dir}")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        with self._driver_lock:
            self._driver = driver

        driver.get("https://web.whatsapp.com")
        logger.info("Waiting for WhatsApp Web to open and settle...")
        time.sleep(WHATSAPP_INITIAL_PAGE_PAUSE_SEC)

        try:
            WebDriverWait(driver, WHATSAPP_LOGIN_TIMEOUT_SEC).until(
                EC.presence_of_element_located((By.ID, "side"))
            )
        except TimeoutException:
            raise RuntimeError("Timed out waiting for WhatsApp login. Please scan the QR code and retry.")

        time.sleep(3)
        return driver

    def _get_or_create_driver(self) -> webdriver.Chrome:
        """
        Reuse the same Chrome window between send batches (required if we do not quit(),
        because a second Chrome cannot use the same user-data-dir while the first is open).
        """
        with self._driver_lock:
            d = self._driver
        if d is not None:
            try:
                _ = d.window_handles
                d.find_element(By.TAG_NAME, "body")
            except Exception as e:
                logger.warning(f"Stored browser session is dead ({e}); launching a new one")
                try:
                    d.quit()
                except Exception:
                    pass
                with self._driver_lock:
                    self._driver = None
            else:
                try:
                    if not d.find_elements(By.ID, "side"):
                        if self.on_progress:
                            self.on_progress(0, 1, "في انتظار تسجيل الدخول في نافذة المتصفح...")
                        WebDriverWait(d, WHATSAPP_LOGIN_TIMEOUT_SEC).until(
                            EC.presence_of_element_located((By.ID, "side"))
                        )
                        time.sleep(2)
                    logger.info("Reusing existing Chrome session for WhatsApp")
                    return d
                except TimeoutException:
                    raise RuntimeError(
                        "Timed out waiting for WhatsApp login. Please scan the QR code in the open browser."
                    )

        return self._create_fresh_driver()

    def _send_messages_worker(
        self,
        phone_numbers: List[str],
        message: str,
        image_path: Optional[str],
    ) -> None:
        """Worker thread for sending messages."""
        success_count = 0
        failed_count = 0
        errors: List[str] = []

        try:
            if self.on_progress:
                self.on_progress(0, len(phone_numbers), "فتح المتصفح والتحقق من الجلسة...")

            driver = self._get_or_create_driver()

            total = len(phone_numbers)
            for index, phone_number in enumerate(phone_numbers, 1):
                if not self.is_sending:
                    logger.info("Sending stopped by user.")
                    break

                try:
                    formatted_phone = self._format_phone_number(phone_number)
                    self._validate_phone_number(formatted_phone)

                    if self.on_progress:
                        self.on_progress(index, total, f"Sending to {formatted_phone}...")

                    abs_image = (
                        os.path.abspath(image_path)
                        if image_path and Path(image_path).is_file()
                        else None
                    )

                    if abs_image:
                        msg_stripped = message.strip()
                        chat_url = f"https://web.whatsapp.com/send?phone={formatted_phone}"
                        driver.get(chat_url)
                        time.sleep(WHATSAPP_CHAT_NAV_PAUSE_SEC)

                        # Send image first, then text immediately after in the same chat.
                        # This is more reliable than media-caption detection across WhatsApp DOM variants.
                        sent_image = self._send_image_message(driver, abs_image, "")
                        if not sent_image:
                            sent = False
                        elif msg_stripped:
                            sent = self._send_followup_text_message(driver, msg_stripped)
                        else:
                            sent = True
                    else:
                        encoded_msg = urllib.parse.quote(message)
                        chat_url = (
                            f"https://web.whatsapp.com/send?phone={formatted_phone}&text={encoded_msg}"
                        )
                        driver.get(chat_url)
                        time.sleep(WHATSAPP_CHAT_NAV_PAUSE_SEC)
                        sent = self._send_current_message(driver)

                    if not sent:
                        raise RuntimeError("Could not trigger send action")
                    success_count += 1

                    # Give WhatsApp a moment to dispatch before next navigation.
                    time.sleep(2)

                    if index < total:
                        delay = random.randint(MIN_DELAY, MAX_DELAY)
                        logger.info(f"Waiting {delay} seconds before next message...")
                        if self.on_progress:
                            self.on_progress(index, total, f"Waiting {delay}s to prevent ban...")
                        time.sleep(delay)

                except Exception as e:
                    failed_count += 1
                    error_msg = f"Failed for {phone_number}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    if self.on_progress:
                        self.on_progress(index, total, f"Error sending to {phone_number}")

        except Exception as e:
            critical_error = f"Critical error: {e}"
            logger.error(critical_error)
            errors.append(critical_error)

        finally:
            # Keep browser open for the next batch and to avoid "profile in use" on re-launch.
            self.is_sending = False
            if self.on_complete:
                self.on_complete(success_count, failed_count, errors)
            logger.info(f"Sending complete. Success: {success_count}, Failed: {failed_count}")

    @staticmethod
    def _visible_send_clickable(driver):
        """Return the best candidate element to activate send (preview or composer)."""
        xpaths = [
            "(//footer//span[@data-icon='send'])[last()]",
            "(//footer//span[@data-icon='wds-ic-send-filled'])[last()]",
            "(//div[@role='application']//span[@data-icon='send'])[last()]",
            "(//span[@data-icon='send'])[last()]",
            "(//span[@data-icon='wds-ic-send-filled'])[last()]",
            "(//*[@data-testid='send'])[last()]",
            "//button[.//span[@data-icon='send'] or .//span[@data-icon='wds-ic-send-filled']]",
            "//div[@role='button'][.//span[@data-icon='send'] or .//span[@data-icon='wds-ic-send-filled']]",
            "//button[contains(@aria-label,'Send') or contains(@aria-label,'إرسال')]",
            "//div[@role='button'][contains(@aria-label,'Send') or contains(@aria-label,'إرسال')]",
        ]
        for xp in xpaths:
            try:
                els = driver.find_elements(By.XPATH, xp)
                for el in reversed(els):
                    try:
                        if el.is_displayed() and el.size.get("height", 0) > 0:
                            return el
                    except Exception:
                        continue
            except Exception:
                continue
        return None

    @classmethod
    def _click_send(cls, driver) -> bool:
        """Try to click the send control (text composer or image/video preview)."""
        time.sleep(0.6)

        send_selectors = [
            "span[data-icon='send']",
            "span[data-icon='wds-ic-send-filled']",
            "[data-testid='send']",
            "span[data-testid='send']",
            "button span[data-icon='send']",
            "div[role='button'] span[data-icon='send']",
            "footer span[data-icon='send']",
        ]

        for sel in send_selectors:
            try:
                el = WebDriverWait(driver, 6).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                if not el.is_displayed():
                    continue
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.25)
                try:
                    el.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", el)
                logger.info(f"Send clicked via selector: {sel}")
                return True
            except Exception:
                continue

        target = cls._visible_send_clickable(driver)
        if target is not None:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
                time.sleep(0.2)
                try:
                    target.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", target)
                logger.info("Send clicked via XPath / visible scan")
                return True
            except Exception:
                pass

        try:
            clicked = driver.execute_script(
                """
                function visible(el) {
                  if (!el) return false;
                  const r = el.getBoundingClientRect();
                  if (r.width < 4 || r.height < 4 || r.bottom < 0 || r.right < 0) return false;
                  const s = window.getComputedStyle(el);
                  return s.display !== 'none' && s.visibility !== 'hidden' && parseFloat(s.opacity) > 0;
                }
                function tryClick(el) {
                  if (!visible(el)) return false;
                  let n = el;
                  for (let i = 0; i < 10 && n; i++) {
                    const tag = (n.tagName || '').toUpperCase();
                    const role = n.getAttribute && n.getAttribute('role');
                    if (tag === 'BUTTON' || role === 'button') {
                      n.click();
                      return true;
                    }
                    n = n.parentElement;
                  }
                  el.click();
                  return true;
                }
                const sels = ['[data-icon="send"]', '[data-icon="wds-ic-send-filled"]', '[data-testid="send"]'];
                for (const s of sels) {
                  const nodes = document.querySelectorAll(s);
                  for (let i = nodes.length - 1; i >= 0; i--) {
                    if (tryClick(nodes[i])) return true;
                  }
                }
                return false;
                """
            )
            if clicked:
                logger.info("Send clicked via script (walk to button parent)")
                return True
        except Exception:
            pass

        try:
            send_icon = driver.find_element(By.CSS_SELECTOR, "span[data-icon='send']")
            driver.execute_script(
                "arguments[0].closest('button,[role=\"button\"],div')?.click();",
                send_icon,
            )
            return True
        except Exception:
            pass

        try:
            el = cls._visible_send_clickable(driver)
            if el:
                ActionChains(driver).move_to_element(el).pause(0.1).click().perform()
                return True
        except Exception:
            pass

        try:
            composer = driver.find_element(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]")
            composer.click()
            composer.send_keys(Keys.ENTER)
            return True
        except Exception:
            return False

    @classmethod
    def _footer_caption_editors(cls, driver):
        """Visible contenteditable nodes in the chat footer (not the contact list / side pane)."""
        found = []
        for sel in (
            "footer div[contenteditable='true']",
            "footer p[contenteditable='true']",
            "footer span[contenteditable='true']",
        ):
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                try:
                    if not el.is_displayed():
                        continue
                    if el.find_elements(By.XPATH, "./ancestor::div[@id='side']"):
                        continue
                    found.append(el)
                except Exception:
                    continue
        return found

    @classmethod
    def _media_row_caption_editors(cls, driver):
        """
        Contenteditable nodes in the same footer as the visible send control (media preview row),
        so we do not type into the main chat line behind the preview.
        """
        xps = (
            "//span[@data-icon='send' or @data-icon='wds-ic-send-filled']"
            "/ancestor::footer[1]//*[self::div or self::p or self::span]"
            "[@contenteditable='true' or @contenteditable='plaintext-only']"
        )
        try:
            els = driver.find_elements(By.XPATH, xps)
            return [e for e in els if e.is_displayed()]
        except Exception:
            return []

    @staticmethod
    def _normalize_caption_text(s: str) -> str:
        return " ".join((s or "").split())

    @classmethod
    def _caption_content_matches(cls, visible_text: str, expected: str) -> bool:
        """Whether the footer/editor text contains the full caption (handles long / RTL)."""
        if not expected or not expected.strip():
            return True
        want = cls._normalize_caption_text(expected)
        got = cls._normalize_caption_text(visible_text)
        if not want:
            return True
        if want in got or got == want:
            return True
        # Long captions: WhatsApp may split lines; require substantial prefix match
        prefix_len = min(80, len(want))
        if prefix_len >= 12 and want[:prefix_len] in got:
            return True
        return False

    @classmethod
    def _caption_verified_in_media_row(cls, driver, caption: str) -> bool:
        """True if expected caption text is present in a visible media-row / footer caption editor."""
        if not caption or not caption.strip():
            return True
        boxes = cls._media_row_caption_editors(driver)
        if not boxes:
            boxes = cls._footer_caption_editors(driver)
        for el in boxes:
            try:
                if cls._caption_content_matches(el.text or "", caption):
                    return True
            except Exception:
                continue
        return False

    @classmethod
    def _type_image_caption(cls, driver, caption: str) -> bool:
        """
        Put caption into the media row and confirm it is visible before send.
        Image+text is not successful unless this returns True when caption is non-empty.
        """
        if not caption or not caption.strip():
            return True
        text = caption.strip()
        time.sleep(0.25)

        for round_idx in range(2):
            boxes = cls._media_row_caption_editors(driver)
            if not boxes:
                boxes = cls._footer_caption_editors(driver)
            if not boxes:
                for el in driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'], p[contenteditable='true']"):
                    try:
                        if not el.is_displayed():
                            continue
                        if el.find_elements(By.XPATH, "./ancestor::div[@id='side']"):
                            continue
                        boxes.append(el)
                    except Exception:
                        continue
            for box in reversed(boxes):
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", box)
                    time.sleep(0.1)
                    box.click()
                    time.sleep(0.15)
                    try:
                        box.send_keys(Keys.CONTROL, "a")
                        time.sleep(0.03)
                        box.send_keys(Keys.BACKSPACE)
                        time.sleep(0.05)
                    except Exception:
                        pass
                except Exception:
                    continue

                inserted = False
                try:
                    driver.execute_cdp_cmd("Input.insertText", {"text": text})
                    inserted = True
                    logger.info("Caption inserted via CDP (media row)")
                except Exception:
                    pass
                if not inserted:
                    try:
                        driver.execute_script(
                            """
                            const t = arguments[0], el = arguments[1];
                            el.focus();
                            el.textContent = '';
                            try {
                                document.execCommand('insertText', false, t);
                            } catch (e) {
                                el.textContent = t;
                            }
                            el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: t }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                            """,
                            text,
                            box,
                        )
                        inserted = True
                        logger.info("Caption inserted via script (media row)")
                    except Exception as e:
                        logger.debug(f"Script caption insert failed: {e}")
                if not inserted:
                    try:
                        box.send_keys(text)
                        inserted = True
                        logger.info("Caption inserted via send_keys (media row)")
                    except Exception as e:
                        logger.warning(f"send_keys caption failed: {e}")

                if inserted:
                    time.sleep(0.35)
                    if cls._caption_verified_in_media_row(driver, caption):
                        return True

            if round_idx == 0:
                time.sleep(0.6)

        logger.error("Caption not verified in media row after typing")
        return False

    @classmethod
    def _footer_visible_blob_images(cls, driver) -> List[Any]:
        """Thumbnail previews in the footer often use blob: URLs."""
        out = []
        try:
            for e in driver.find_elements(By.CSS_SELECTOR, "footer img"):
                try:
                    if not e.is_displayed():
                        continue
                    src = (e.get_attribute("src") or "").strip()
                    if src.startswith("blob:"):
                        out.append(e)
                except Exception:
                    continue
        except Exception:
            pass
        return out

    @classmethod
    def _wait_media_send_confirmed(cls, driver, had_blob_preview: bool) -> bool:
        """
        After clicking send on media, wait until the preview UI clears so we do not
        report success while WhatsApp is still composing or uploading.
        """
        deadline = time.time() + WHATSAPP_MEDIA_SEND_CONFIRM_TIMEOUT_SEC
        hold_sec = float(WHATSAPP_MEDIA_POST_CLEAR_HOLD_SEC)
        cleared_at: Optional[float] = None

        if not had_blob_preview:
            # No blob thumb detected; wait a fixed window for send pipeline
            time.sleep(12)
            logger.info("No blob preview detected; used fixed post-send wait")
            return True

        while time.time() < deadline:
            blobs = cls._footer_visible_blob_images(driver)
            if not blobs:
                if cleared_at is None:
                    cleared_at = time.time()
                elif time.time() - cleared_at >= hold_sec:
                    logger.info("Media preview cleared after send")
                    return True
            else:
                cleared_at = None
            time.sleep(0.45)

        logger.error("Timeout waiting for media preview to clear (send may be incomplete)")
        return False

    @classmethod
    def _send_current_message(cls, driver) -> bool:
        """
        Send the current prefilled WhatsApp message (from URL text=).
        """
        WebDriverWait(driver, WHATSAPP_COMPOSER_WAIT_SEC).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true']"))
        )
        return cls._click_send(driver)

    @classmethod
    def _send_followup_text_message(cls, driver, text: str) -> bool:
        """
        Send text immediately after a media send in the same chat.
        Success means both image and text were sent.
        """
        if not text or not text.strip():
            return True

        msg = text.strip()
        editors = []
        for sel in (
            "footer div[contenteditable='true']",
            "footer p[contenteditable='true']",
            "footer span[contenteditable='true']",
            "div[contenteditable='true'][data-tab]",
            "div[contenteditable='true']",
        ):
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                try:
                    if not el.is_displayed():
                        continue
                    if el.find_elements(By.XPATH, "./ancestor::div[@id='side']"):
                        continue
                    editors.append(el)
                except Exception:
                    continue

        for box in reversed(editors):
            try:
                box.click()
                time.sleep(0.12)
                try:
                    box.send_keys(Keys.CONTROL, "a")
                    time.sleep(0.03)
                    box.send_keys(Keys.BACKSPACE)
                except Exception:
                    pass

                inserted = False
                try:
                    driver.execute_cdp_cmd("Input.insertText", {"text": msg})
                    inserted = True
                except Exception:
                    pass
                if not inserted:
                    try:
                        box.send_keys(msg)
                        inserted = True
                    except Exception:
                        pass

                if not inserted:
                    continue

                time.sleep(0.2)
                if cls._click_send(driver):
                    logger.info("Follow-up text sent after image")
                    return True
            except Exception:
                continue

        logger.error("Could not send follow-up text after image")
        return False

    @classmethod
    def _send_image_message(cls, driver, image_abs_path: str, caption: str) -> bool:
        """
        Upload an image via hidden file inputs, optional caption, then send.
        """
        WebDriverWait(driver, WHATSAPP_COMPOSER_WAIT_SEC).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "footer"))
        )

        path_str = str(Path(image_abs_path).resolve())
        if os.name == "nt":
            path_str = path_str.replace("/", "\\")

        uploaded = False
        for inp in driver.find_elements(By.CSS_SELECTOR, "input[type='file']"):
            try:
                accept = (inp.get_attribute("accept") or "").lower()
                if accept and "image" not in accept and "video" not in accept and "*" not in accept:
                    continue
                inp.send_keys(path_str)
                uploaded = True
                logger.info("Image path sent to file input")
                break
            except Exception:
                continue

        if not uploaded:
            for inp in driver.find_elements(By.CSS_SELECTOR, "input[type='file']"):
                try:
                    inp.send_keys(path_str)
                    uploaded = True
                    logger.info("Image path sent to generic file input")
                    break
                except Exception:
                    continue

        if not uploaded:
            for sel in (
                "span[data-icon='plus']",
                "span[data-icon='plus-rounded']",
                "span[data-icon='attach-menu-plus']",
                "span[data-icon='clip']",
            ):
                try:
                    driver.find_element(By.CSS_SELECTOR, sel).click()
                    time.sleep(1.5)
                    break
                except Exception:
                    continue
            for inp in driver.find_elements(By.CSS_SELECTOR, "input[type='file']"):
                try:
                    inp.send_keys(path_str)
                    uploaded = True
                    logger.info("Image uploaded after opening attach menu")
                    break
                except Exception:
                    continue

        if not uploaded:
            logger.error("No usable file input for image upload")
            return False

        time.sleep(WHATSAPP_IMAGE_PREVIEW_WAIT_SEC)

        # Media preview can render send control late; wait for any send-like element.
        try:
            WebDriverWait(driver, 25).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, "[data-icon='send']")
                or d.find_elements(By.CSS_SELECTOR, "[data-testid='send']")
                or d.find_elements(By.CSS_SELECTOR, "[data-icon='wds-ic-send-filled']")
            )
            time.sleep(1.5)
        except TimeoutException:
            logger.warning("No send control detected yet after image preview wait; trying anyway")

        # Caption must be visible in the media row before send; otherwise fail (no "image-only" success).
        if caption and caption.strip():
            if not cls._type_image_caption(driver, caption):
                raise RuntimeError(
                    "لم يُثبت النص في تعليق الصورة؛ تم إلغاء الإرسال لتجنب إرسال الصورة بدون الرسالة."
                )
            time.sleep(0.45)

        had_blob_preview = len(cls._footer_visible_blob_images(driver)) > 0

        clicked = False
        if cls._click_send(driver):
            clicked = True
        else:
            for attempt in range(2, 4):
                logger.warning(f"Send click attempt {attempt}/3 failed, retrying...")
                time.sleep(2.5)
                if cls._click_send(driver):
                    clicked = True
                    break
        if not clicked:
            raise RuntimeError("Could not trigger send action")

        if not cls._wait_media_send_confirmed(driver, had_blob_preview):
            raise RuntimeError(
                "انتهت مهلة انتظار واتساب بعد الضغط على إرسال؛ قد لا يكون الإرسال اكتمل. أعد المحاولة."
            )
        return True

    @staticmethod
    def _format_phone_number(phone: str) -> str:
        """
        Format phone number for WhatsApp Web URL.
        Returns digits only, country code included (no leading '+').
        """
        cleaned = (
            phone.replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
            .replace("+", "")
        )

        # 00<country><number> -> <country><number>
        if cleaned.startswith("00"):
            cleaned = cleaned[2:]

        # Local Israel format 0XXXXXXXXX -> 972XXXXXXXXX
        if cleaned.startswith("0"):
            cleaned = "972" + cleaned[1:]

        return cleaned

    @staticmethod
    def _validate_phone_number(phone: str) -> None:
        """Validate phone number as digits-only international format."""
        if not re.fullmatch(r"\d{8,15}", phone):
            raise ValueError(
                f"Invalid phone format '{phone}'. Use digits with country code (example: 9725XXXXXXXX)."
            )

        if phone.startswith("0"):
            raise ValueError(
                f"Invalid phone format '{phone}'. Country code cannot start with 0."
            )

    def stop_sending(self) -> None:
        """Stop the current sending loop."""
        self.is_sending = False
        logger.info("Stop signal sent to sender thread")
