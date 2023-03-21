# Forexbotly
# TODO: This project is a work in progress
Forexbotly is a Python-based bot that uses the IG API to implement a trading strategy for forex markets. The bot uses technical analysis to identify market stages and calculate support and resistance levels for various currency pairs. It also implements three different trading strategies for different market stages.

**Note: the strategies used here are untested, please use at your own risk and manage you money wisely. Backtest every strategy that you implement.**

## Setup and Running the Bot
To set up the bot and run it on your machine, you can follow these steps:

1. Clone the repository from GitHub using `git clone https://github.com/digiphd/Forexbotly.git`
2. Install the required packages using `pip install -r requirements.txt`.
3. Copy the config_sample.ini file and rename it to config.ini.
4. Edit the config.ini file and add your IG account credentials and API key.
5. In the app.py file, update the acc_type and currency_pairs variables to match your trading preferences.
6. Run the bot using the command `python app.py`



## Parameters to Configure
You can configure several parameters in the app.py file to customize the bot's behavior:

1. `username`: your IG account username.
2. `password`: your IG account password.
3. `api_key`: your IG account API key.
4. `acc_type`: your account type, either "DEMO" or "LIVE".
5. `currency_pairs`: a list of currency pairs to trade.
6. `resolution`: the resolution of the historical data to fetch.
7. `test`: a boolean flag indicating whether to run the bot in test mode or not.
8. `window`: the window size to use for calculating support and resistance levels.
9. `size`: the size of the trade to place.
10. `stop_distance`: the distance of the stop loss from the entry price.
11. `limit_distance`: the distance of the take profit from the entry price.

By modifying these parameters, you can customize the bot's behavior to suit your trading preferences.