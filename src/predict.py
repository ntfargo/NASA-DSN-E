import pandas as pd
import pickle
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

class DSNPredictor:
    def __init__(self, ml_config):
        self.model_path = ml_config["model_path"]
        self.training_data = ml_config["training_data"]
        self.features = ml_config["features"]
        self.target = ml_config["target"]
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            with open(self.model_path, "rb") as f:
                self.model = pickle.load(f)
                print("Loaded existing model.")
        except FileNotFoundError:
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
            print("Initialized new model.")

    def train_model(self):
        try:
            df = pd.read_csv(self.training_data)
            X = df[self.features]
            y = df[self.target]
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            self.model.fit(X_train, y_train)
            score = self.model.score(X_test, y_test)
            print(f"Model trained. R^2 score: {score:.2f}")
            with open(self.model_path, "wb") as f:
                pickle.dump(self.model, f)
            print("Model saved.")
        except Exception as e:
            print(f"Training failed: {e}")

    def is_trained(self):
        return hasattr(self.model, 'estimators_') and self.model.estimators_ is not None

    def predict(self, data):
        if self.model is None:
            print("No model available. Train first.")
            return None
        if not self.is_trained():
            print("Model not trained yet. Train first.")
            return None
        try:
            df = pd.DataFrame(data, columns=self.features)
            predictions = self.model.predict(df)
            return predictions
        except Exception as e:
            print(f"Prediction failed: {e}")
            return None