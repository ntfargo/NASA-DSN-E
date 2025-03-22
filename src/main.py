import os
import yaml
import time
import threading
from monitor import DSNMonitor
from predict import DSNPredictor
from webapp import create_app

def load_config(config_path="config/settings.yaml"):
    with open(config_path, "r") as file:
        return yaml.safe_load(file)

def data_fetching_loop(monitor, predictor, scrape_interval, retrain_interval, emit_update):
    last_retrain = time.time()
    while True:
        try:
            data = monitor.fetch_dsn_data()
            monitor.store_data(data)
            print("Data fetched and stored successfully.")
            
            # Emit update through WebSocket
            emit_update(data)

            current_time = time.time()
            if current_time - last_retrain >= retrain_interval:
                predictor.train_model()
                last_retrain = current_time
                print("Model retrained.")

            time.sleep(scrape_interval)

        except Exception as e:
            print(f"Error in data fetching loop: {e}")
            time.sleep(scrape_interval)

def main():
    config = load_config()
    print("Starting NASA-DSN-E... Configuration loaded.")

    monitor = DSNMonitor(config["data"], config["database"])
    predictor = DSNPredictor(config["ml"])
    app, socketio, emit_update = create_app(config["webapp"], monitor, predictor)

    scrape_interval = config["data"]["scrape_interval"]
    retrain_interval = config["ml"]["retrain_interval"]
    data_thread = threading.Thread(
        target=data_fetching_loop,
        args=(monitor, predictor, scrape_interval, retrain_interval, emit_update),
        daemon=True
    )
    data_thread.start()
    print(f"Started data fetching thread (interval: {scrape_interval} seconds)")

    socketio.run(
        app,
        host=config["webapp"]["host"],
        port=config["webapp"]["port"],
        debug=config["webapp"]["debug"]
    )

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")
    main()