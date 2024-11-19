import os
import time
import pyfiglet
import shutil
from colorama import Fore, Style

def display_progress(scraped, total, info_type, font='digital'):
    # os.system('cls' if os.name == 'nt' else 'clear')  # Clear console
    
    # Display the type of info being scraped
    print(f"{Fore.CYAN}Scraping {info_type}...{Style.RESET_ALL}\n")

    # Create the "scraped / total" string and convert it to ASCII art
    progress_text = f"{scraped}/{total}"
    terminal_width = shutil.get_terminal_size().columns

    # Adjust the ASCII art width to be about 60% of the terminal width
    ascii_art_width = int(terminal_width)
    ascii_art = pyfiglet.figlet_format(progress_text, font=font, width=ascii_art_width)
    
    # Split the ASCII art into lines for line-by-line animation
    ascii_lines = ascii_art.splitlines()

    for line in ascii_lines:
        print(line.center(terminal_width))

    
    print("\n")  # Adding a newline after the art

def test(text: str, font):
    print(pyfiglet.figlet_format(text, font=font, width=shutil.get_terminal_size().columns).center(shutil.get_terminal_size().columns))

def clear():
    os.system('cls' if os.name in ['nt'] else 'clear')


if __name__ == '__main__':
    for font in pyfiglet.FigletFont().getFonts():
        test('Hellow world', font)
        input('Press enter to see more...')
        os.system('cls')
