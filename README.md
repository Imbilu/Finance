# Finance

This is a web app that allows you to manage portfolios of stocks. You can check real stocks' actual prices and portfolios' values, and buy and sell stocks by querying IEX for stocks' prices.

## Usage

1. First, you will need to get an API key from IEX (free account registration), which lets you download stock quotes via their API (application programming interface) using URLs like https://cloud.iexapis.com/stable/stock/nflx/quote?token=API_KEY.
2. Clone this repository to your local machine.
3. In the terminal, navigate to the directory where you cloned this repository.
4. Run `pip install -r requirements.txt` to install all the required packages.
5. Run `flask run` to start the web app.
6. Open your web browser and go to http://localhost:5000.

## Implementation

This web app is built using Flask, SQLite3, and Bootstrap. The following files are included in this repository:

- `app.py`: This file contains the main Flask application.
- `helpers.py`: This file contains helper functions used in `app.py`.
- `finance.db`: This file contains the SQLite3 database.
- `templates/`: This directory contains all the HTML templates used in the web app.
- `static/`: This directory contains all the static files used in the web app.

## Credits

This project is part of the CS50x course offered by Harvard University. The starter code for this project was provided by the course staff.
