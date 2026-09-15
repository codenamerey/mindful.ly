import hashlib
import json
import os
import threading
from pathlib import Path


class CodexAuth:
    def __init__(self, *, client_factory, begin_browser_login, exchange_code, begin_device_login, complete_device_login, pending_file, notify, transfer_profile=None, tracker_url_validator=lambda value: value):
        self.client_factory = client_factory
        self.begin_browser_login = begin_browser_login
        self.exchange_code = exchange_code
        self.begin_device_login = begin_device_login
        self.complete_device_login = complete_device_login
        self.pending_file = Path(pending_file)
        self.notify = notify
        self.transfer_profile = transfer_profile
        self.tracker_url_validator = tracker_url_validator
        self.lock = threading.Lock()
        self.state = {"status": "idle", "verification_url": None, "user_code": None, "error": None}

    def account(self):
        client = None
        try:
            client = self.client_factory(interactive=False, timeout_seconds=20)
            account = client.account_info()
            return {"authenticated": bool(account.get("authenticated")), "email": account.get("email"), "plan_type": account.get("plan_type")}
        except Exception:
            return {"authenticated": False, "email": None, "plan_type": None}
        finally:
            if client is not None:
                client.close()

    def profile_key(self, identity):
        normalized = str(identity or "").strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:32] if normalized else ""

    def set_profile_cookie(self, response, account, *, cookie_name="learner_profile"):
        profile = self.profile_key((account or {}).get("email"))
        if profile:
            if self.transfer_profile:
                self.transfer_profile(profile)
            response.set_cookie(cookie_name, profile, max_age=63072000, httponly=True, samesite="Lax")
        return response

    def start_browser(self, tracker_url):
        authorization_url, verifier, state = self.begin_browser_login()
        payload = {"state": state, "verifier": verifier, "tracker_url": self.tracker_url_validator(tracker_url)}
        self.pending_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.pending_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload), encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(self.pending_file)
        with self.lock:
            self.state = {"status": "pending", "verification_url": authorization_url, "user_code": None, "error": None}
        return dict(self.state)

    def finish_browser(self, code, state):
        try:
            pending = json.loads(self.pending_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return self.fail("No pending Codex login; start a new login.")
        if pending.get("state") != state:
            return self.fail("OAuth state mismatch; start a new login.")
        try:
            account = self.exchange_code(code, pending["verifier"])
            self.pending_file.unlink(missing_ok=True)
        except Exception as error:
            return self.fail(str(error))
        with self.lock:
            self.state = {"status": "authenticated", "verification_url": None, "user_code": None, "error": None, **account, "tracker_url": pending["tracker_url"]}
        self.notify()
        return dict(self.state)

    def start_device(self):
        try:
            device = self.begin_device_login()
        except Exception as error:
            return self.fail(str(error))
        with self.lock:
            self.state = {"status": "pending", "verification_url": device.verification_url, "user_code": device.user_code, "error": None}
        threading.Thread(target=self._poll_device, args=(device,), daemon=True).start()
        return dict(self.state)

    def _poll_device(self, device):
        try:
            account = self.complete_device_login(device)
        except Exception as error:
            self.fail(str(error))
            return
        with self.lock:
            self.state = {"status": "authenticated", "verification_url": None, "user_code": None, "error": None, **account}
        self.notify()

    def fail(self, message):
        with self.lock:
            self.state = {"status": "error", "verification_url": None, "user_code": None, "error": message}
        self.notify()
        return dict(self.state)
