# Trip Splitter

Group trip expenses: everyone adds what they paid, the app shows **who pays whom**.
Each trip is a private link (`/?trip=<random id>`), stored as one JSON file. No login.

## Run
    pip install -r requirements.txt
    streamlit run app.py
    python -m pytest          # calculation tests

## Share
Open a trip, expand "Share this trip", send the link (WhatsApp button included).
Anyone with the link can view/add/edit; trips are isolated from each other.

## Deploy (so friends can reach it)
Run it on any server/VPS/Docker host: `streamlit run app.py --server.port 8501`.
Keep trip files on a persistent disk and point `TRIP_DATA_DIR` at it.
Streamlit Community Cloud has temporary storage, so use the in-app JSON backup there.

## Layout
calc.py (pure money logic) · storage.py (JSON files, swap for a DB later) · app.py (UI) · test_calc.py
