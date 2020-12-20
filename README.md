# CS:GO Marketplace Webscraper
This script scrapes price data from the CS:GO community market and analyzes whether it would be a good item to "flip" (buy low and sell high). The items that are checked are listed in csgoskins.csv which contains an outdated list of all skins in the game. Relevant data about skins is output to file data.txt. The file line.txt stores which line the program is on so that the program can be stopped and start where it left off. 

### Todo
* Reformat to work with updated skin list
* Add functionality to work with non-weapon skin items (e.g cases, pins, etc)
* Implement better way to exit program
* Add threading to improve performance
