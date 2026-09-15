import urllib.parse

from flask import Blueprint, jsonify, redirect, request


def create_codex_login_blueprint(*, auth, client_factory, available_models, selected_model, persist_model, cookie_name="learner_profile"):
    blueprint = Blueprint("codex_login", __name__)

    @blueprint.get("/api/codex/auth")
    def status():
        account = auth.account()
        if account["authenticated"]:
            return auth.set_profile_cookie(jsonify({"status": "authenticated", **account}), account, cookie_name=cookie_name)
        with auth.lock:
            return jsonify({"authenticated": False, **auth.state})

    @blueprint.post("/api/codex/login")
    def login():
        account = auth.account()
        if account["authenticated"]:
            return auth.set_profile_cookie(jsonify({"status": "authenticated", **account}), account, cookie_name=cookie_name)
        state = auth.start_device()
        return (jsonify({"authenticated": False, **state}), 503) if state["status"] == "error" else jsonify({"authenticated": False, **state})

    @blueprint.get("/auth/callback")
    def callback():
        result = auth.finish_browser(request.args.get("code", ""), request.args.get("state", ""))
        if result.get("status") != "authenticated":
            return jsonify(result), 400
        response = redirect(result["tracker_url"])
        return auth.set_profile_cookie(response, result, cookie_name=cookie_name)

    @blueprint.post("/api/codex/complete")
    def complete():
        callback_url = str((request.get_json(silent=True) or {}).get("callback_url", "")).strip()
        parsed = urllib.parse.urlsplit(callback_url)
        if parsed.scheme not in {"http", "https"} or parsed.path.rstrip("/") != "/auth/callback":
            return jsonify({"error": "Invalid Codex callback URL"}), 400
        values = dict(urllib.parse.parse_qsl(parsed.query))
        result = auth.finish_browser(values.get("code", ""), values.get("state", ""))
        if result.get("status") != "authenticated":
            return jsonify(result), 400
        return auth.set_profile_cookie(jsonify({"ok": True, **result}), result, cookie_name=cookie_name)

    @blueprint.post("/api/codex/logout")
    def logout():
        client = None
        try:
            client = client_factory(interactive=False, timeout_seconds=20)
            client.logout()
        except Exception as error:
            return jsonify({"error": f"Could not log out of Codex: {error}"}), 503
        finally:
            if client is not None:
                client.close()
        with auth.lock:
            auth.state = {"status": "idle", "verification_url": None, "user_code": None, "error": None}
        response = jsonify({"ok": True, "authenticated": False, "status": "idle"})
        response.delete_cookie(cookie_name)
        return response

    @blueprint.get("/api/codex/models")
    def models():
        client = None
        try:
            client = client_factory(interactive=False, timeout_seconds=30)
            choices = [item for item in available_models(client) if item.supported_in_api is not False]
        except Exception as error:
            return jsonify({"error": f"Could not load Codex models: {error}"}), 503
        finally:
            if client is not None:
                client.close()
        selected = selected_model()
        if choices and selected not in {item.id for item in choices}:
            selected = choices[0].id
            persist_model(selected)
        return jsonify({"selected": selected, "models": [{"id": item.id, "name": item.display_name or item.id, "description": item.description} for item in choices]})

    @blueprint.post("/api/codex/model")
    def model():
        requested = str((request.get_json(silent=True) or {}).get("model", "")).strip()
        if not requested:
            return jsonify({"error": "Select a Codex model"}), 400
        client = None
        try:
            client = client_factory(interactive=False, timeout_seconds=30)
            chosen = next((item for item in available_models(client) if item.id == requested and item.supported_in_api is not False), None)
        except Exception as error:
            return jsonify({"error": f"Could not select Codex model: {error}"}), 400
        finally:
            if client is not None:
                client.close()
        if chosen is None:
            return jsonify({"error": "Model is not available"}), 400
        persist_model(requested)
        return jsonify({"ok": True, "model": requested, "name": chosen.display_name or requested})

    return blueprint
