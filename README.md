# Angelica the Bot
*Epic 7 Discord Bot*

Want to request catalysts from your Epic 7 guild every day but feel bad for accepting too much charity? Worried that some people always request catalysts without donating back while others only get runes? Have a bunch of different catalysts that you don't currently need and would like to exchange them for other ones at an acceptable rate? **Angelica the Bot** is here to make it all a fair trade!

Rare catalysts is a valubale resource in Epic 7 and it can be a long grind to fully upgrade your hero, especially for newer players. This bot allows you to exchange catalysts at **1:1** rate within your guild instead of the expensive crafts, by keeping track of everyone's exchange scores. Be efficient with **Angelica** and save up on rare catalysts to craft epic ones instead.

<img src="https://camo.githubusercontent.com/f0d885ecd8979a3544ad104ea3665dab81c7b657/68747470733a2f2f692e696d6775722e636f6d2f72434f5833426f2e706e67" data-canonical-src="https://i.imgur.com/rCOX3Bo.png" width="600" />

# Features:
+ Request catalysts with a search support, thank the assistant user and notify your guild members when you donate yourself 
+ View the Guild Board with everyone's current exchange scores, active requests and all time assistance scores
+ Quickly look up all the catalysts, their respective signs and heroes that use them (coming soon)
+ Gift your exchange points to other guild members if you feel generous, allowing them to request even more
+ Set the minimum score threshold after reaching which users won't be able to request more, before improving their score

# Setup
Invite [Angelica](https://discordapp.com/api/oauth2/authorize?client_id=635517667222224902&permissions=51200&scope=bot) to your server and it's ready to go! Use **!ahelp** to see all available commands and **!how** for a quick visual tutorial on how to use the bot. 

In order to use admin commands, setup the Discord role which will correspond to the bot admin role using !adminrole, default admin role is "**Angelica's Crew**". Changing the role requires Discord "**Manage Role**" permissions.

Bot uses "**!**" and "**a!**" prefixes.

# Recommendations
After inviting **Angelica** it is adviced to make a guild rule to request catalysts by using the bot always. The more people participate - the easier it is for everyone to get exact catalysts they want.

Setting too low minimum threshold or holding on too much positive exchange score is not recommended, points should shuffle back into the economy allowing users more options to donate/request.

The bot works with non Discord users as well, in this case after receiving the aid and using **!thanks @Angelica** you'll get **+1** points, as if they said **!thanks** to you also for donating back, but since non Discord guildies don't actively participate in bot exchange economy, it's up to you whenever you actually want to donate them back or take a free point.

# Commands
Arguments should be provided without <, > brackets

#### All users:
+ !ahelp - Shows all commands
+ !how - Quick visual tutorial that shows how to use the bot
+ !request <catalyst_query> - Requests named catalysts, -2 to points
+ !thanks <@user> - Thanks the user who provided the assistance, +1 points to the user
+ !aid <@user> - Notifies user about your aid, optional command
+ !board - Guild board with user scores and active requests
+ !gift <@user> - Gifts 1 of your points to the mentioned user
+ !catalysts - Shows neat picture with all the catalysts
+ !signs <sign_name> - Your daily horoscope

#### Admin only:
+ !adminrole <role_id> or <role_name> - Sets bot admin role, requires discord role management permissions to call, pass no arguments to view current role
+ !minscore <score> - Sets the minimum score threshold value
+ !cancel <@user> - Cancels current request and refunds remaining points
+ !remove <@user> or <user_discord_id> - Removes user from the board
+ !setscore <@user new_score> - Sets the score manually, should only be used in cases of malfunction

# Future plans:
+ Allow admins to save and load backup with a command
+ Add more features/games that would fit Epic 7 theme

# Credits
**Sasha#8102** on [Epic 7 Official Discord](https://discordapp.com/invite/officialepicseven) - DM me if you have any questions or suggestions. Thanks to my guild for ideas and testing
