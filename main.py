import os
import logging
import asyncio
import traceback
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from strategies.btc_strategy import BTCStrategy
from strategies.eth_strategy import ETHStrategy
from strategies.sol_strategy import SOLStrategy
from utils.kucoin_client import KuCoinClient

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class CryptoTradingBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
            raise ValueError("Missing TELEGRAM_BOT_TOKEN")

        self.kucoin_client = KuCoinClient(
            api_key=os.getenv('KUCOIN_API_KEY', ''),
            api_secret=os.getenv('KUCOIN_API_SECRET', ''),
            api_passphrase=os.getenv('KUCOIN_API_PASSPHRASE', '')
        )

        self.strategies = {
            'BTC': BTCStrategy(self.kucoin_client),
            'ETH': ETHStrategy(self.kucoin_client),
            'SOL': SOLStrategy(self.kucoin_client)
        }

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        try:
            keyboard = [
                [
                    InlineKeyboardButton("📈 BTC Strategy", callback_data='strategy_BTC'),
                    InlineKeyboardButton("💎 ETH Strategy", callback_data='strategy_ETH'),
                    InlineKeyboardButton("⚡ SOL Strategy", callback_data='strategy_SOL')
                ],
                [
                    InlineKeyboardButton("📊 All Signals", callback_data='all_signals'),
                    InlineKeyboardButton("ℹ️ Help", callback_data='help')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            welcome_text = '''🤖 **Crypto Trading Bot** 🚀

Select a strategy to get live signals with:
✅ Support & Resistance levels
✅ Order book analysis  
✅ Entry/Exit points
✅ Risk management

Choose an asset below:'''

            await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("❌ Bot startup error. Please try again.")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries"""
        query = update.callback_query
        await query.answer()

        try:
            if query.data.startswith('strategy_'):
                symbol = query.data.split('_')[1]
                await self.send_strategy_signal(query, symbol)
            elif query.data == 'all_signals':
                await self.send_all_signals(query)
            elif query.data == 'help':
                await self.send_help(query)
            elif query.data == 'back_to_menu':
                await self.back_to_menu(query)

        except Exception as e:
            logger.error(f"Callback error: {e}")
            await query.edit_message_text("❌ Error processing request. Please try again.")

    async def send_strategy_signal(self, query, symbol):
        """Send strategy signal for specific symbol"""
        try:
            await query.edit_message_text(f"🔄 Analyzing {symbol} strategy... Please wait.")

            strategy = self.strategies[symbol]
            signal = await strategy.get_signal()

            if signal:
                message = self.format_signal_message(signal)
                keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"❌ No signal available for {symbol} right now.", reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Strategy signal error: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"❌ Error getting {symbol} signal. Please try again.", reply_markup=reply_markup)

    async def send_all_signals(self, query):
        """Send all strategy signals"""
        try:
            await query.edit_message_text("🔄 Fetching all signals... Please wait.")

            all_signals = []
            for symbol, strategy in self.strategies.items():
                try:
                    signal = await strategy.get_signal()
                    if signal and signal.get('side') != 'HOLD':
                        all_signals.append(f"**{symbol}:** {signal['side']} @ ${signal['entry']:.2f}")
                    else:
                        all_signals.append(f"**{symbol}:** No signal")
                except:
                    all_signals.append(f"**{symbol}:** Error")

            message = "📊 **All Strategy Signals**\n\n" + "\n".join(all_signals)
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"All signals error: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("❌ Error fetching signals.", reply_markup=reply_markup)

    async def send_help(self, query):
        """Send help message"""
        help_text = '''📖 **How to Use This Bot**

**Strategies:**
🔹 **BTC**: Trend Rider with S/R filter
🔹 **ETH**: Mean Reversion + Breakout
🔹 **SOL**: Momentum Scalper

**Features:**
✅ Real-time market analysis
✅ Support & Resistance levels
✅ Order book imbalance detection
✅ Entry/Exit recommendations
✅ Risk management alerts

**Commands:**
/start - Main menu
/status - Bot status

**Note:** This is for educational purposes only. Trade at your own risk.'''

        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

    def format_signal_message(self, signal):
        """Format signal data into readable message"""
        if not signal:
            return "❌ No signal available"

        side_emoji = "🟢" if signal['side'] == 'LONG' else "🔴" if signal['side'] == 'SHORT' else "⚪"

        message = f'''{side_emoji} **{signal['symbol']} - {signal['side']} SIGNAL**

⚡ **Entry:** ${signal['entry']:.2f}
🛑 **Stop Loss:** ${signal['stop_loss']:.2f}
🎯 **Take Profit:** ${signal['take_profit']:.2f}

📐 **Support/Resistance:**
S1: ${signal['sr_levels']['S1']:.2f} | R1: ${signal['sr_levels']['R1']:.2f}
S2: ${signal['sr_levels']['S2']:.2f} | R2: ${signal['sr_levels']['R2']:.2f}

📊 **Order Book:**
{signal['orderbook_bias']}

🎲 **Confidence:** {signal['confidence']:.0%}

**Strategy:** {signal.get('strategy_name', 'N/A')}
**Time:** {datetime.now().strftime('%H:%M:%S UTC')}

⚠️ *Educational purposes only. Trade at your own risk.*'''
        return message

    async def back_to_menu(self, query):
        """Handle back to menu button"""
        keyboard = [
            [
                InlineKeyboardButton("📈 BTC Strategy", callback_data='strategy_BTC'),
                InlineKeyboardButton("💎 ETH Strategy", callback_data='strategy_ETH'),
                InlineKeyboardButton("⚡ SOL Strategy", callback_data='strategy_SOL')
            ],
            [
                InlineKeyboardButton("📊 All Signals", callback_data='all_signals'),
                InlineKeyboardButton("ℹ️ Help", callback_data='help')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = '''🤖 **Crypto Trading Bot** 🚀

Select a strategy to get live signals with:
✅ Support & Resistance levels
✅ Order book analysis  
✅ Entry/Exit points
✅ Risk management

Choose an asset below:'''

        await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Status command"""
        try:
            status_text = f'''🤖 **Bot Status: ONLINE** ✅

🔗 **Connections:**
• KuCoin API: {'✅ Connected' if self.kucoin_client else '❌ Error'}
• Telegram: ✅ Connected

📈 **Supported Assets:**
• BTC/USDT (Trend Rider)
• ETH/USDT (Mean Reversion)
• SOL/USDT (Scalper)

🕒 **Uptime:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}'''

            await update.message.reply_text(status_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Status error: {e}")
            await update.message.reply_text("❌ Error getting status.")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")

        if update and update.effective_message:
            await update.effective_message.reply_text("❌ An error occurred. Please try again.")

def main():
    """Main function"""
    try:
        # Initialize bot
        bot = CryptoTradingBot()

        # Create application
        application = Application.builder().token(bot.token).build()

        # Add handlers
        application.add_handler(CommandHandler("start", bot.start))
        application.add_handler(CommandHandler("status", bot.status))
        application.add_handler(CallbackQueryHandler(bot.handle_callback))

        # Add error handler
        application.add_error_handler(bot.error_handler)

        # Get port from environment (for Render)
        port = int(os.environ.get('PORT', 8443))

        logger.info("Starting Crypto Trading Bot...")

        # For Render deployment - use webhook
        webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/{bot.token}"

        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=bot.token,
            webhook_url=webhook_url
        )

    except Exception as e:
        logger.error(f"Bot startup error: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    main()