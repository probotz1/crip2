import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)  # Use __name__ instead of name

# Replace 'YOUR_BOT_TOKEN' with your actual bot token
TOKEN = '7214008691:AAGieVATScjKHOiii77o6kr9d6922hJgbaU'

# A simple dictionary to store links
links = {}

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Welcome to the Crunchyroll Link Manager Bot! Use /add <URL> to add a link and /list to list all saved links.')

def add(update: Update, context: CallbackContext) -> None:
    url = ' '.join(context.args)
    user_id = update.message.from_user.id
    if not url:
        update.message.reply_text('Please provide a Crunchyroll video URL.')
        return

    if user_id not in links:
        links[user_id] = []

    links[user_id].append(url)
    update.message.reply_text(f'Link added: {url}')
    logger.info(f'Link added: {url} by user: {user_id}')

def list_links(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in links or not links[user_id]:
        update.message.reply_text('No links saved yet.')
        return

    response = 'Saved links:\n' + '\n'.join(links[user_id])
    update.message.reply_text(response)
    logger.info(f'Listed links for user: {user_id}')

def main():
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('add', add))
    dispatcher.add_handler(CommandHandler('list', list_links))

    logger.info('Bot started')
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':  # Correct the condition for main execution
    app.run()
