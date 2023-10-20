**BOT FEATURES**
- Audio stream
- Queue management (removing and reordering tracks, skipping etc)
- Audio pausing/resuming
- Slash commands 

**HOW TO USE**

🟣 `/play` queues/plays a track (title or url) or a playlist (url only)

🟣 `/skip`  skips to next track in queue

🟣 `/tracklist` displays current queue

🟣 `/pause` pauses, `/resume` resumes 

🟣 `/now` shows currently playing song

🟣 `/clear` clears the queue

🟣 `/stop` clears queue and stops current session

🟣 `/rm` removes a track from a queue

**SETUP**

[The following text guide is courtesy of repl.it](https://replit.com/@replit/Discordpy-Music-Bot)

### Pre-Setup

If you don't already have a discord bot, click [here](https://discordapp.com/developers/), accept any prompts then click "New Application" at the top right of the screen.  Enter the name of your bot then click accept.  Click on Bot from the panel from the left, then click "Add Bot."  When the prompt appears, click "Yes, do it!" 
![Left panel](https://i.imgur.com/hECJYWK.png)

Then, click copy under token to get your bot's token. Your bot's icon can also be changed by uploading an image.

![Bot token area](https://i.imgur.com/da0ktMC.png)

### Setup

Create a file named `.env`

Add `TOKEN=<your bot token>`

Your .env file should look something like this:

```
TOKEN=<Bot token>
```

### Uptime

To keep your bot alive you need to make this repl into a webserver. The way you do that is that you `import keep_alive` (file included this repl) and call it `keep_alive()`.

Now that this repl is a server, all you have to do to keep your bot up is setup something to ping the site your bot made every 5 minutes or so.

Go to [uptimerobot.com](https://uptimerobot.com/) and create an accout if you dont have one.  After verifying your account, click "Add New Monitor".

+ For Monitor Type select "HTTP(s)"
+ In Friendly Name put the name of your bot
+ For your url, put the url of the website made for your repl.
+ Select any alert contacts you want, then click "Create Monitor" 
![Uptime robot example](https://i.imgur.com/Qd9LXEy.png)

Your bot should now be good to go, with near 100% uptime.

