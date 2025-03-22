# NASA-DSN-E

NASA-DSN-E is a Python-based tool enhancing Deep Space Network monitoring with real-time visualizations, predictive analytics, and machine learning for JPL mission support and public engagement.

## Overview

The NASA Deep Space Network (DSN) is critical for communicating with spacecraft across the solar system. NASA-DSN-E builds on the open-source DSN Monitor project to fetch real-time data from [DSNNow](https://eyes.nasa.gov/dsn/dsn.html), offering enhanced features like historical analysis, predictive communication insights, and an interactive web dashboard. Developed with Python, this project aims to support JPL’s operations and educate the public about deep space missions.

## Features

- Real-Time Monitoring: Visualize current DSN spacecraft communications.
- Historical Analysis: Track and graph past DSN activity.
- Predictive Analytics: Use machine learning to forecast communication patterns.
- Web Dashboard: Access insights through an intuitive interface.

## Installation

1. Clone the Repository:
   git clone https://github.com/ntfargo/NASA-DSN-E.git
   cd NASA-DSN-E

2. Set Up a Virtual Environment (optional but recommended):
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install Dependencies:
   pip install -r requirements.txt

4. Configure Settings:
   - Edit config/settings.yaml with your preferences (e.g., API endpoints, model parameters).

## Usage

1. Run the Main Script:
   python src/main.py

2. Access the Web Dashboard:
   - Open your browser to http://localhost:5000 after starting the app.

3. Example Output:
   - View real-time DSN activity graphs and predictions for upcoming communication windows.
 
## Dependencies

- Python 3.8+
- Libraries: pandas, scikit-learn, flask, requests, matplotlib (see requirements.txt)

## Contributing

We welcome contributions! To get started:
1. Fork the repository.
2. Create a feature branch (git checkout -b feature-name).
3. Commit your changes (git commit -m "Add feature").
4. Push to your branch (git push origin feature-name).
5. Open a Pull Request.

Please follow the [Code of Conduct](docs/CODE_OF_CONDUCT.md) and check the [issues page](https://github.com/ntfargo/NASA-DSN-E/issues) for tasks.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments
 
- Inspired by NASA’s open-source initiatives and JPL’s Deep Space Network.