# UI Usage

Run the API first:

```powershell
uvicorn main:app --reload
```

Then serve the UI from the `ui` folder:

```powershell
cd "d:\SHL - Assesment\ui"
python -m http.server 5500
```

Open:

- http://127.0.0.1:5500

The UI sends the full conversation history to `POST /chat` on every turn, so it respects the backend's stateless design.
