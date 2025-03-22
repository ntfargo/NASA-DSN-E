from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import json
from datetime import datetime
import re
import logging

def create_app(web_config, monitor, predictor):
    app = Flask(__name__)
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    @app.template_filter('strftime')
    def _jinja2_filter_datetime(date, fmt=None):
        if fmt is None:
            fmt = "%b %d, %I:%M %p"
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except ValueError:
                date = datetime.strptime(date, "%b %d, %I:%M %p")
        return date.strftime(fmt)

    def generate_plot(data):
        timestamps = [d["timestamp"] for d in data]
        strengths = [d["signal_strength"] for d in data]
        plt.figure(figsize=(10, 5))
        plt.plot(timestamps, strengths, marker="o")
        plt.title("DSN Signal Strength Over Time")
        plt.xlabel("Timestamp")
        plt.ylabel("Signal Strength")
        plt.xticks(rotation=45)
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plot_url = base64.b64encode(buf.getvalue()).decode("utf8")
        plt.close()
        return plot_url

    @app.route("/")
    def index():
        data = monitor.fetch_dsn_data()
        if data:
            predictions = predictor.predict([d for d in data])
            if predictions is not None:
                for i, d in enumerate(data):
                    d["communication_duration"] = float(predictions[i])
                    d["timestamp"] = _jinja2_filter_datetime(d["timestamp"])
            else:
                for d in data:
                    d["communication_duration"] = 0.0
                    d["timestamp"] = _jinja2_filter_datetime(d["timestamp"])
        plot_url = generate_plot(data) if data else None
        return render_template("index.html", data=data, plot_url=plot_url, title=web_config["title"])

    @socketio.on('connect')
    def handle_connect():
        print('Client connected')
        data = monitor.fetch_dsn_data()
        if data:
            predictions = predictor.predict([d for d in data])
            if predictions is not None:
                for i, d in enumerate(data):
                    d["communication_duration"] = float(predictions[i])
                    d["timestamp"] = _jinja2_filter_datetime(d["timestamp"])
            else:
                for d in data:
                    d["communication_duration"] = 0.0
                    d["timestamp"] = _jinja2_filter_datetime(d["timestamp"])
        plot_url = generate_plot(data) if data else None
        socketio.emit('update_data', {'data': data, 'plot_url': plot_url})

    def emit_update(data):
        if data:
            predictions = predictor.predict([d for d in data])
            if predictions is not None:
                for i, d in enumerate(data):
                    d["communication_duration"] = float(predictions[i])
                    d["timestamp"] = _jinja2_filter_datetime(d["timestamp"])
            else:
                for d in data:
                    d["communication_duration"] = 0.0
                    d["timestamp"] = _jinja2_filter_datetime(d["timestamp"])
        plot_url = generate_plot(data) if data else None
        socketio.emit('update_data', {'data': data, 'plot_url': plot_url})

    @app.route("/spacecraft_details")
    def spacecraft_details():
        try:
            spacecraft_name = request.args.get("spacecraft_name")
            antenna = request.args.get("antenna")
            start_time = request.args.get("start")
            end_time = request.args.get("end")
            
            logger.debug(f"Received request with parameters: spacecraft_name={spacecraft_name}, antenna={antenna}")
            logger.debug(f"start_time={start_time}, end_time={end_time}")
            
            if not all([spacecraft_name, antenna, start_time, end_time]):
                return jsonify({"error": "Missing required parameters"}), 400
            
            # Validate and parse start_time and end_time
            try:
                start_timestamp = datetime.strptime(start_time, "%a, %d %b %Y %H:%M:%S GMT")
                end_timestamp = datetime.strptime(end_time, "%a, %d %b %Y %H:%M:%S GMT")
                logger.debug(f"Parsed start_timestamp: {start_timestamp}, end_timestamp: {end_timestamp}")
            except ValueError as e:
                logger.error(f"Error parsing timestamp: {e}")
                return jsonify({"error": f"Invalid timestamp format: {str(e)}"}), 400
            
            data = monitor.fetch_dsn_data()
            if not data:
                logger.warning("No data available from monitor")
                return jsonify({"error": "No data available"}), 404
            
            logger.debug(f"Fetched {len(data)} records from monitor")
            
            if data:
                logger.debug(f"Sample monitor timestamp: {data[0].get('timestamp')}")
            
            filtered_data = [d for d in data if 
                           d.get("spacecraft") == spacecraft_name and 
                           d.get("antenna_id") == antenna]
            
            logger.debug(f"Filtered to {len(filtered_data)} matching records (before timestamp filter)")
            
            if not filtered_data:
                logger.warning(f"No matching data found for spacecraft={spacecraft_name}, antenna={antenna}")
                return jsonify({"error": "No data found for specified parameters"}), 404
            
            spacecraft_data = filtered_data[0]
            logger.debug(f"Selected spacecraft data: {spacecraft_data}")
            
            try:
                response = {
                    "spacecraft": spacecraft_data.get("spacecraft", "N/A"),
                    "data_rate": f"{spacecraft_data.get('data_rate', 'N/A')} bps",
                    "power": f"{float(spacecraft_data.get('signal_strength', 0)):.1f} dBm",
                    "frequency": f"{float(spacecraft_data.get('frequency', 0))/1e9:.2f} GHz",
                    "range": f"{spacecraft_data.get('spacecraft_range', 'N/A')} km"
                }
                logger.debug(f"Formatted response: {response}")
                return jsonify(response)
            except (ValueError, TypeError) as e:
                logger.error(f"Error formatting response: {e}")
                return jsonify({"error": f"Error formatting data: {str(e)}"}), 500
            
        except Exception as e:
            logger.error(f"Unexpected error in spacecraft_details: {str(e)}", exc_info=True)
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    return app, socketio, emit_update