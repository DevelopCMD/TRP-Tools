import discord
import ffmpeg
from discord.ext import commands
from discord import Game
from ffmpeg import probe
import os
import math
import random
import uuid
import subprocess
import time  # For measuring processing time

# Bot setup
intents = discord.Intents.all()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="trp!", intents=intents, help_command=None)

# Ensure the 'tmp' directory exists in the bot's current working directory
TMP_DIR = "tmp"
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

# Valid file types for video and audio
VALID_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.webm', '.avi']
VALID_AUDIO_EXTENSIONS = ['.mp3', '.wav']

MAX_FILE_SIZE_MB = 25

async def validate_attachment(attachment):
    if attachment.size > MAX_FILE_SIZE_MB * 1024 * 1024:  # Convert MB to bytes
        raise ValueError(f"File size exceeds the {MAX_FILE_SIZE_MB} MB limit.")

def get_file_metadata(file_path):
    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)  # Convert to MB

    try:
        metadata = probe(file_path)
        video_streams = [stream for stream in metadata.get('streams', []) if stream['codec_type'] == 'video']
        if video_streams:
            width = video_streams[0].get('width', 'Unknown')
            height = video_streams[0].get('height', 'Unknown')
            resolution = f"{width}x{height}"
        else:
            resolution = None
    except Exception:
        resolution = None  # In case probe fails

    return f"{file_size_mb:.2f} MB", resolution

async def get_target_media(ctx):
    if ctx.message.attachments:
        return ctx.message.attachments[0]

    if ctx.message.reference:
        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        if ref_msg.attachments:
            return ref_msg.attachments[0]

    async for message in ctx.channel.history(limit=50):
        if message.attachments:
            return message.attachments[0]

    return None

def process_video(input_path, output_path, action, value=None):
    # Ensure the file paths are correct
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    
    if os.path.exists(output_path):
        os.remove(output_path)  # Remove the file if it already exists

    try:
        # Prepare FFmpeg command depending on action
        if action == "speed":
            speed = float(value) if value else 1.0
            command = [
                "ffmpeg", "-i", input_path,
                "-filter:v", f"setpts={1/speed}*PTS",
                "-filter:a", f"atempo={speed}",
                "-y", output_path
            ]
        elif action == "reverse":
            command = ["ffmpeg", "-i", input_path, "-vf", "reverse", "-af", "areverse", "-y", output_path]
        elif action == "invert":
            command = ["ffmpeg", "-i", input_path, "-vf", "negate", "-y", output_path]
        elif action == "rotate180":
            command = ["ffmpeg", "-i", input_path, "-vf", "transpose=2,transpose=2", "-y", output_path]
        elif action == "flipv":
            command = ["ffmpeg", "-i", input_path, "-vf", "vflip", "-y", output_path]
        elif action == "fliph":
            command = ["ffmpeg", "-i", input_path, "-vf", "hflip", "-y", output_path]
        elif action == "contrast":
            if not value:
                raise ValueError("Contrast value must be provided.")
            command = ["ffmpeg", "-i", input_path, "-vf", f"eq=contrast={value}", "-y", output_path]
        elif action == "blackandwhite":
            command = ["ffmpeg", "-i", input_path, "-vf", "hue=s=0", "-y", output_path]
        elif action == "hue":
            if not value:
                raise ValueError("Hue value must be provided.")
            command = ["ffmpeg", "-i", input_path, "-vf", f"hue=h={value}", "-y", output_path]
        elif action == "blur":
            if not value:
                value = "1.0"  # Default blur strength
            command = ["ffmpeg", "-i", input_path, "-vf", f"gblur=sigma={value}", "-y", output_path]
        elif action == "mosaic":
            # Mosaic creates a 2x2 grid of the same video
            command = [
                "ffmpeg",
                "-i", input_path,
                "-filter_complex", "[0:v]tile=2x2",
                "-c:v", "libx264",
                "-preset", "fast",
                "-y", output_path
            ]
        else:
            raise ValueError("Invalid action")

        # Run FFmpeg command directly using subprocess for error capture
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg encountered an error: {e.stderr}")

def process_audio(input_path, output_path, action, value=None):
    # Ensure the file paths are correct
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    
    if os.path.exists(output_path):
        os.remove(output_path)  # Remove the file if it already exists

    try:
        # Prepare FFmpeg command depending on action
        if action == "speed":
            speed = float(value) if value else 1.0
            command = ["ffmpeg", "-i", input_path, "-filter:a", f"atempo={speed}", "-y", output_path]
        elif action == "reverse":
            command = ["ffmpeg", "-i", input_path, "-af", "areverse", "-y", output_path]
        else:
            raise ValueError("Invalid action")
        
        # Run FFmpeg command directly using subprocess for error capture
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg encountered an error: {e.stderr}")

def process_image(input_path, output_path, action, value=None):
    try:
        if action == "flipv":
            command = ["ffmpeg", "-i", input_path, "-vf", "vflip", "-y", output_path]
        elif action == "fliph":
            command = ["ffmpeg", "-i", input_path, "-vf", "hflip", "-y", output_path]
        elif action == "invert":
            command = ["ffmpeg", "-i", input_path, "-vf", "negate", "-y", output_path]
        elif action == "hue":
            if not value:
                raise ValueError("Hue value must be provided.")
            command = ["ffmpeg", "-i", input_path, "-vf", f"hue=h={value}", "-y", output_path]
        elif action == "contrast":
            if not value:
                raise ValueError("Contrast value must be provided.")
            command = ["ffmpeg", "-i", input_path, "-vf", f"eq=contrast={value}", "-y", output_path]
        elif action == "blackandwhite":
            command = ["ffmpeg", "-i", input_path, "-vf", "hue=s=0", "-y", output_path]
        else:
            raise ValueError("Invalid action")

        # Run FFmpeg command
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg encountered an error: {e.stderr}")

@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user}")
    # Set the bot's status
    await bot.change_presence(
        activity=Game(name="with your files "),
        status=discord.Status.dnd  # Can be online, idle, dnd (do not disturb), or invisible
    )

@bot.command(name="video")
async def video(ctx, action: str, value: str = None):
    attachment = await get_target_media(ctx)

    if not attachment:
        await ctx.send("No video file found to edit.")
        return

    file_extension = os.path.splitext(attachment.filename)[1].lower()

    # Check if it's a valid video file
    if file_extension not in VALID_VIDEO_EXTENSIONS:
        await ctx.send("Invalid file type for video. Please upload a valid video file (e.g., .mp4, .mov, .avi, .webm).")
        return

    # Generate a random unique filename for input and output video files
    input_filename = f"{TMP_DIR}/{uuid.uuid4()}{file_extension}"
    output_filename = f"{TMP_DIR}/{uuid.uuid4()}.mp4"  # Default output format for video

    try:
        # Download the video file
        await attachment.save(input_filename)

        # Ensure a valid action and process the video
        valid_actions = ["speed", "reverse", "invert", "rotate180", "flipv", "fliph", "contrast", "blackandwhite", "blur", "hue", "mosaic"]
        if action not in valid_actions:
            await ctx.send(f"Invalid action. Supported actions: {', '.join(valid_actions)}.")
            return

        # Start typing indicator while processing
        async with ctx.channel.typing():
            # Measure the start time
            start_time = time.time()

            # Process the video using FFmpeg
            process_video(input_filename, output_filename, action, value)

            # Measure the end time and calculate the duration
            end_time = time.time()
            processing_time = end_time - start_time

        # Check if output file exists after processing
        if not os.path.exists(output_filename):
            await ctx.send("Error: The processed video file could not be created.")
            return

        # Build and send the response
        await ctx.reply(f"-# Took {processing_time:.2f} seconds", file=discord.File(output_filename))

    
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
    finally:
        # Cleanup - Try removing the files after processing
        if os.path.exists(input_filename):
            os.remove(input_filename)
        if os.path.exists(output_filename):
            os.remove(output_filename)

@bot.command(name="audio")
async def audio(ctx, action: str, value: str = None):
    attachment = await get_target_media(ctx)

    if not attachment:
        await ctx.send("No audio file found to edit.")
        return

    file_extension = os.path.splitext(attachment.filename)[1].lower()

    # Check if it's a valid audio file
    if file_extension not in VALID_AUDIO_EXTENSIONS:
        await ctx.send("Invalid file type for audio. Please upload a valid audio file (e.g., .mp3, .wav).")
        return

    # Generate a random unique filename for input and output audio files
    input_filename = f"{TMP_DIR}/{uuid.uuid4()}{file_extension}"
    output_filename = f"{TMP_DIR}/{uuid.uuid4()}.mp3"  # Default output format for audio

    try:
        # Download the audio file
        await attachment.save(input_filename)

        # Ensure a valid action and process the audio
        if action not in ["speed", "reverse"]:
            await ctx.send("Invalid action. Use `speed` or `reverse`.")
            return

        # Start typing indicator while processing
        async with ctx.channel.typing():
            # Measure the start time
            start_time = time.time()

            # Process the audio using FFmpeg
            process_audio(input_filename, output_filename, action, value)

            # Measure the end time and calculate the duration
            end_time = time.time()
            processing_time = end_time - start_time

        # Check if output file exists after processing
        if not os.path.exists(output_filename):
            await ctx.send("Error: The processed audio file could not be created.")
            return

        # Build and send the response
        await ctx.reply(f"-# Took {processing_time:.2f} seconds", file=discord.File(output_filename))
    
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
    finally:
        # Cleanup - Try removing the files after processing
        if os.path.exists(input_filename):
            os.remove(input_filename)
        if os.path.exists(output_filename):
            os.remove(output_filename)

@bot.command(name="image")
async def image(ctx, action: str, value: str = None):
    attachment = await get_target_media(ctx)

    if not attachment:
        await ctx.send("No image file found to edit.")
        return

    file_extension = os.path.splitext(attachment.filename)[1].lower()

    # Check if it's a valid image file
    VALID_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp", ".gif"]
    if file_extension not in VALID_IMAGE_EXTENSIONS:
        await ctx.send("Invalid file type for image. Please upload a valid image file (e.g., .jpg, .png).")
        return

    input_filename = f"{TMP_DIR}/{uuid.uuid4()}{file_extension}"
    output_filename = f"{TMP_DIR}/{uuid.uuid4()}.png"  # Default output format for images

    try:
        # Download the image file
        await attachment.save(input_filename)

        # Ensure a valid action and process the image
        valid_actions = ["flipv", "fliph", "invert", "hue", "contrast", "blackandwhite"]
        if action not in valid_actions:
            await ctx.send(f"Invalid action. Supported actions: {', '.join(valid_actions)}.")
            return

        async with ctx.channel.typing():
            start_time = time.time()
            process_image(input_filename, output_filename, action, value)
            end_time = time.time()
            processing_time = end_time - start_time

        if not os.path.exists(output_filename):
            await ctx.send("Error: The processed image file could not be created.")
            return

        # Build and send the response
        await ctx.reply(f"-# Took {processing_time:.2f} seconds", file=discord.File(output_filename))

    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
    finally:
        if os.path.exists(input_filename):
            os.remove(input_filename)
        if os.path.exists(output_filename):
            os.remove(output_filename)

@bot.command(name="ping")
async def ping(ctx):
    latency = bot.latency  # Bot latency in seconds
    latency_ms = round(latency * 1000, 2)  # Convert to milliseconds and round
    await ctx.reply(f"**Pong! 🏓** Latency: {latency_ms} ms")

@bot.command(name="randnum")
async def randnum(ctx):
    number = random.randint(1, 100)
    await ctx.reply(f"**Number:** {number}")

@bot.command(name="help")
async def about_bot(ctx):
    embed = discord.Embed(
        title="TRP Tools - Help",
        description="A list of commands for TRP Tools, a better version of JERN Utilites by jwklong.",
        color=discord.Color.blue()
    )

    # Video commands
    video_commands = """
    `trp!video speed <value>` - Change the speed of a video (e.g., `2` for double speed).
    `trp!video reverse` - Reverse the video.
    `trp!video invert` - Invert the colors of a video.
    `trp!video rotate180` - Rotate the video by 180 degrees.
    `trp!video flipv` - Flip the video vertically.
    `trp!video fliph` - Flip the video horizontally.
    `trp!video contrast <value>` - Adjust the contrast of a video.
    `trp!video blackandwhite` - Convert the video to grayscale.
    `trp!video hue <value>` - Adjust the hue of a video.
    `trp!video blur <value>` - Apply a blur effect to a video.
    `trp!video mosaic` - Apply a mosaic effect to a video.
    """
    embed.add_field(name="Video Commands", value=video_commands, inline=False)

    # Audio commands
    audio_commands = """
    `trp!audio speed <value>` - Change the speed of an audio file.
    `trp!audio reverse` - Reverse the audio file.
    """
    embed.add_field(name="Audio Commands", value=audio_commands, inline=False)

    # Image commands
    image_commands = """
    `trp!image flipv` - Flip the image vertically.
    `trp!image fliph` - Flip the image horizontally.
    `trp!image invert` - Invert the colors of an image.
    `trp!image hue <value>` - Adjust the hue of an image.
    `trp!image contrast <value>` - Adjust the contrast of an image.
    `trp!image blackandwhite` - Convert the image to grayscale.
    """
    embed.add_field(name="Image Commands", value=image_commands, inline=False)

    # General commands
    general_commands = """
    `trp!ping` - Test the bot's latency.
    `trp!randnum` - Chooses a random number.
    `trp!help` - Show this help message.
    """
    embed.add_field(name="General Commands", value=general_commands, inline=False)

    # Send the embed
    await ctx.send(embed=embed)

# Run the bot
bot.run("YOUR-API-KEY-HERE")
