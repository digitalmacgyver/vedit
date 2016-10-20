vedit Overview
================================================================================

Project homepage at: https://github.com/digitalmacgyver/vedit

vedit is a Python library that simplifies editing and combining video files using ``ffmpeg``.

Examples of the sorts of things vedit makes easy include:

- Extracting a clip from a longer video
- Combining videos or clips together by concatenating them end to end
- Composing videos together, for example side by side or overlayed on top of a background image
- Changing the resolution of a video and cropping or padding a video to change its aspect ratio
- Overlaying images onto a video
- Adding an audio track (like a song) to a video

There are numerous stumbling blocks to these tasks - vedit makes the above things easy by automatically handling videos with:

- Different resolutions
- Different sample aspect ratios
- Different pixel formats
- Different frame rates
- Different audio streams and channels

Installation
================================================================================

Assuming you have ``pip`` installed:

    pip install vedit

However, there is nothing in the package that is special, and no
Python dependencies other than a Python 2.7 interpreter with the
standard library, you can just download from the project GitHub
repository and put the ``vedit`` directory in your Python path.

Before You Begin
================================================================================

vedit depends on the ``ffmpeg`` and ``ffprobe`` programs from the FFmpeg_ project, and on the libx264 video codec and the libfdk_aac audio codec, for example by configuring ``ffmpeg`` for compilation with:

    ./configure --enable-gpl --enable-libx264 --enable-nonfree --enable-libfdk-aac --enable-libfreetype --enable-libfontconfig

(``--enable-libfreetype --enable-libfontconfig`` only needed if the ``audio_desc`` option is used).

.. _FFmpeg: https://ffmpeg.org/

Table of Contents
================================================================================

- `Examples`_

  - `Example 1: Clip 2 seconds out of the middle of a video`_
  - `Example 2: Resize a video with PAD, CROP, or PAN`_
  - `Example 3: Put two videos next to each other`_
  - `Example 4: Replace the audio track of a video`_
  - `Example 5: Overlay videos on top of other videos`_
  - `Example 6: Cascade overlayed videos and images on top of a base video or image`_
  - `Example 7: Add an overlay image, such as a watermark`_

- `Module Concepts`_

  - `Windows`_
  - `Display Configuration`_
  - `Videos and Clips`_
  - `Watermarks`_
  - `Audio`_

- `Logging Output`_
- `Getting Help`_
- `Contributing`_
- `Odds and Ends`_

Examples
================================================================================

To get an idea of the sorts of things you can do with a few lines of code, consider these examples, which can be generated from the ``examples.py`` script in the root directory of the ``vedit`` Python module.

All the examples below assume that FFmpeg_ is installed as described in `Before You Begin`_.

All the examples below begin with the following boilerplate, and assume the ``./example_output`` directory exists: ::

  #!/usr/bin/env python
  
  import vedit
  import logging
  logging.basicConfig()
  log = logging.getLogger()
  log.setLevel( logging.DEBUG )
   
Back to `Table of Contents`_

Example 1: Clip 2 seconds out of the middle of a video
--------------------------------------------------------------------------------

Link to input for example: https://youtu.be/9ul6rWAewd4

Link to example output: https://youtu.be/FEr6WMUx_4A

::

    # Clipping 2 seconds out of source video from 1.5 seconds to 3.5 seconds.
    source = vedit.Video( "./examples/testpattern.mp4" )
    output_file = "./example_output/example01.mp4"
    clip = vedit.Clip( video=source, start=1.5, end=3.5 )
    window = vedit.Window( width=source.get_width(), 
                           height=source.get_height(),
                           output_file=output_file )
    window.clips = [ clip ]
    window.render()
    log.info( "Output file at %s" % ( output_file ) )

Back to `Table of Contents`_

Example 2: Resize a video with PAD, CROP, or PAN
--------------------------------------------------------------------------------

Link to source input: https://youtu.be/Qmbgrr6WJEY

Links to example outputs:

- Padded clip: https://youtu.be/2bTdwEzraxA
- Panned clip: https://youtu.be/lCpbnudnFyc
- Cropped clip: https://youtu.be/96v-KVq9B-g

::

    # Turning a 1280x720 16:9 input video into a 640x480 4:3 video.
    source = vedit.Video( "./examples/d005.mp4" )
    clip = vedit.Clip( video=source )

    #Since the input and output aspect ratios don't match, pad the input onto a blue background.
    pad_output = "./example_output/example02-pad.mp4"
    pad_display = vedit.Display( display_style=vedit.PAD, pad_bgcolor="Blue" )
    window = vedit.Window( width=640, height=480, 
                           display=pad_display, 
                           output_file=pad_output )
    window.clips = [ clip ]
    window.render()
    log.info( "Pad output file at: %s" % ( pad_output ) )

    # Render a cropped version as well. Note the watermark is getting cropped out on the right.
    crop_output = "./example_output/example02-crop.mp4"
    crop_display = vedit.Display( display_style=vedit.CROP )
    window = vedit.Window( width=640, height=480, 
                           display=crop_display, 
                           output_file=crop_output )
    window.clips = [ clip ]
    window.render()
    log.info( "Crop output file at: %s" % ( crop_output ) )

    # Render a version where we pan over the input image as it plays as well. Note the watermark moves from left to right.
    pan_output = "./example_output/example02-pan.mp4"
    pan_display = vedit.Display( display_style=vedit.PAN )
    window = vedit.Window( width=640, height=480, 
                           display=pan_display, 
                           output_file=pan_output )
    window.clips = [ clip ]
    window.render()
    log.info( "Pan output file at: %s" % ( pan_output ) )

Back to `Table of Contents`_

Example 3: Put two videos next to each other
--------------------------------------------------------------------------------

Example output: https://youtu.be/fsYw2jLyuQ4

::

    # Lets set up some source videos, and some clips for use below.
    video_1 = vedit.Video( "./examples/i030.mp4" )

    # Put two clips from video 1 side by side, with audio from the
    # left clip only, ending after 8 seconds (we could also use clips
    # from different videos).
    clip_1_0_5 = vedit.Clip( video=video_1, start=0, end=5 )
    clip_1_10_20 = vedit.Clip( video=video_1, start=10, end=20,
                               display=vedit.Display( include_audio=False ) )

    # Set up two windows, one for each clip, and one to hold the other two, and set the duration.
    #
    # Since clip 1 is 5 seconds long and we are making an 8 second
    # video, there will be time when clip 1 is not playing - set the
    # background color to green during this time.
    output_file = "./example_output/example03.mp4"
    base_window = vedit.Window( width=1280*2, height=720, duration=8, bgcolor='Green',
                                output_file=output_file )
    # Set the x, y coordinates of this window inside its parent, as
    # measure from the top right.
    #
    # Here we are putting the videos flush side by side, but they
    # could be on top of each other, overlapping, centered in a much
    # larger base_window, etc., etc..
    clip_1_window = vedit.Window( width=1280, height=720, x=0, y=0, clips=[ clip_1_0_5 ] )
    clip_2_window = vedit.Window( width=1280, height=720, x=1280, y=0, clips=[ clip_1_10_20 ] )
    base_window.windows = [ clip_1_window, clip_2_window ]
    base_window.render()
    log.info( "Side by side output is at: %s" % ( output_file ) )


Back to `Table of Contents`_

Example 4: Replace the audio track of a video
--------------------------------------------------------------------------------

Example outputs:
 
- Not attributed: https://youtu.be/4Z2Uigssc88
- Attributed song: https://youtu.be/ojgAs5A5bSg

::

    source = vedit.Video( "./examples/i010.mp4" )
    output_file = "./example_output/example04.mp4"
    # Get a clip, but override any Window settings for its audio.
    clip = vedit.Clip( video=source, display=vedit.Display( include_audio=False ) )
    # Give this window it's own audio track, and set the duration to
    # 10 seconds (otherwise it will go on as long as the audio track).
    #
    # Note - if the window audio track is longer than the video
    # content, it fades out starting 5 seconds from the end.
    window = vedit.Window( audio_file="./examples/a2.mp4", duration=10,
                           output_file=output_file )
    window.clips = [ clip ]
    window.render()
    log.info( "Replaced audio in output: %s" % ( output_file ) )

    # Let's make a version where we attribute the audio with some text.
    song_attribution = '''This video features the song:
    Chuckie Vs Hardwell Vs Sandro Silva Vs Cedric & Quintino
    EPIC CLARITY JUMP- (NC MASHUP) LIVE
    By: NICOLE CHEN
    Available under under a Creative Commons License:
    http://creativecommons.org/licenses/by/3.0/ license'''

    output_file = "./example_output/example04-attributed.mp4"
    window = vedit.Window( audio_file="./examples/a2.mp4", 
                           audio_desc=song_attribution,
                           duration=10,
                           output_file=output_file )
    window.clips = [ clip ]
    window.render()
    log.info( "Replaced audio in output: %s" % ( output_file ) )

Back to `Table of Contents`_

Example 5: Overlay videos on top of other videos
--------------------------------------------------------------------------------

Example outputs:

- All audio tracks (bleagh): https://youtu.be/lqLLlXPYg3c
- Just one audio track: https://youtu.be/hL0t3RXHKAM

::

    # Let's overlay two smaller windows on top of a base video.
    base_video = vedit.Video( "./examples/i030.mp4" )
    base_clip = vedit.Clip( video=base_video )
    output_file = "./example_output/example05.mp4"
    # Use the default width, height, and display parameters:
    # 1280x1024, which happens to be the size of this input.
    base_window = vedit.Window( clips = [ base_clip ],
                                output_file=output_file )

    # We'll create two smaller windows, each 1/3 the size of the
    # base_window, and position them towards the top left, and bottom
    # right of the base window.
    overlay_window1 = vedit.Window( width=base_window.width/3, height=base_window.height/3,
                                    x=base_window.width/12, y=base_window.height/12 )
    overlay_window2 = vedit.Window( width=base_window.width/3, height=base_window.height/3,
                                    x=7*base_window.width/12, y=7*base_window.height/12 )
    
    # Now let's put some clips in each of the overlay windows.
    window_1_clips = [
        vedit.Clip( video=vedit.Video( "./examples/d007.mp4" ) ),
        vedit.Clip( video=vedit.Video( "./examples/d006.mp4" ) ),
    ]
    window_2_clips = [
        vedit.Clip( video=vedit.Video( "./examples/p006.mp4" ) ),
        vedit.Clip( video=vedit.Video( "./examples/p007.mp4" ) ),
        vedit.Clip( video=vedit.Video( "./examples/p008.mp4" ) ),
    ]

    # Now let's embed the clips in the windows, and the overlay
    # windows in our base_window and render.
    overlay_window1.clips = window_1_clips
    overlay_window2.clips = window_2_clips
    base_window.windows = [ overlay_window1, overlay_window2 ]
    base_window.render()
    log.info( "Made multi-video composition at: %s" % ( output_file ) )

    # Well - the last video looks OK, but it sounds terrible - the
    # audio from all the videos are being mixed together.
    #
    # Let's try again but exclude audio from everything but the base
    # video.
    output_file = "./example_output/example05-single-audio.mp4"
    no_audio_display_config = vedit.Display( include_audio=False )
    no_audio_overlay_window1 = vedit.Window( width=base_window.width/3, height=base_window.height/3,
                                    x=base_window.width/12, y=base_window.height/12,
                                    display=no_audio_display_config )
    no_audio_overlay_window2 = vedit.Window( width=base_window.width/3, height=base_window.height/3,
                                    x=7*base_window.width/12, y=7*base_window.height/12,
                                    display=no_audio_display_config )
    
    # Now let's embed the clips in the windows, and the overlay
    # windows in our base_window and render.
    no_audio_overlay_window1.clips = window_1_clips
    no_audio_overlay_window2.clips = window_2_clips
    base_window.output_file = output_file
    base_window.windows = [ no_audio_overlay_window1, no_audio_overlay_window2 ]
    base_window.render()
    log.info( "Made multi-video composition with single audio track at: %s" % ( output_file ) )

Back to `Table of Contents`_

Example 6: Cascade overlayed videos and images on top of a base video or image
--------------------------------------------------------------------------------

Example output: https://youtu.be/K2SuPqWrG3M

::

    import glob
    import random

    # The OVERLAY display_style when applied to a clip in the window
    # makes it shrink a random amount and be played while it scrolls
    # across the base window.
    #
    # Let's use that to combine several things together and make a
    # huge mess!
    output_file = "./example_output/example06.mp4"
    base_video = vedit.Video( "./examples/i030.mp4" )

    # Let's use a different audio track for this.
    base_clip = vedit.Clip( video=base_video, display=vedit.Display( include_audio=False ) )
    base_window = vedit.Window( clips = [ base_clip ],
                                output_file=output_file,
                                duration=30,
                                audio_file="./examples/a2.mp4" )

    # Turn our cat images into clips of random length between 3 and 6
    # seconds and have them cascade across the screen from left to
    # right.
    cat_display = vedit.Display( display_style=vedit.OVERLAY,
                                 overlay_direction=vedit.RIGHT,
                                 include_audio=False,
                                 overlay_concurrency=4,
                                 overlay_min_gap=0.8 )
    cat_clips = []
    for cat_pic in glob.glob( "./examples/cat*jpg" ):
        cat_video_file = vedit.gen_background_video( bgimage_file=cat_pic,
                                                     duration=random.randint( 3, 6 ) )
        cat_video = vedit.Video( cat_video_file )
        cat_clips.append( vedit.Clip( video=cat_video, display=cat_display ) )

    # Turn our dog images into clips of random length between 2 and 5
    # seconds and have them cascade across the screen from top to
    # bottom.
    dog_display = vedit.Display( display_style=vedit.OVERLAY,
                                 overlay_direction=vedit.DOWN,
                                 include_audio=False,
                                 overlay_concurrency=4,
                                 overlay_min_gap=0.8 )
    dog_clips = []
    for dog_pic in glob.glob( "./examples/dog*jpg" ):
        dog_video_file = vedit.gen_background_video( bgimage_file=dog_pic,
                                                     duration=random.randint( 3, 6 ) )
                                                     
        dog_video = vedit.Video( dog_video_file )
        dog_clips.append( vedit.Clip( video=dog_video, display=dog_display ) )
    
    # Throw in the clips from the p series of videos of their full
    # duration cascading from bottom to top.
    pvideo_display = vedit.Display( display_style=vedit.OVERLAY,
                                    overlay_direction=vedit.UP,
                                    include_audio=False,
                                    overlay_concurrency=4,
                                    overlay_min_gap=0.8 )
    pvideo_clips = []
    for p_file in glob.glob( "./examples/p0*mp4" ):
        pvideo_video = vedit.Video( p_file )
        pvideo_clips.append( vedit.Clip( video=pvideo_video, display=pvideo_display ) )
    
    # Shuffle all the clips together and add them onto the existing
    # clips for the base_window.
    overlay_clips = cat_clips + dog_clips + pvideo_clips
    random.shuffle( overlay_clips )
    base_window.clips += overlay_clips
    base_window.render()
    log.info( "Goofy mashup of cats, dogs, and drone videos over Icelandic countryside at: %s" % ( output_file ) )


Note: Since the composition of this video involves several random
elements, the output you get will not be the same as the example
output below.

Back to `Table of Contents`_

Example 7: Add an overlay image, such as a watermark
--------------------------------------------------------------------------------

Example output: https://youtu.be/1PrADMtqdRU

::

    import glob

    # Let's make our background an image with a song.
    output_file = "./example_output/example07.mp4"
    dog_background = vedit.Window( bgimage_file="./examples/dog03.jpg",
                                   width=960, #The dimensions of this image
                                   height=640,
                                   duration=45,
                                   audio_file="./examples/a3.mp4",
                                   output_file=output_file )
    
    # Let's put two windows onto this image, one 16:9, and one 9:16.
    horizontal_window = vedit.Window( width = 214,
                                     height = 120,
                                     x = (960/2-214)/2, # Center it horizontally on the left half.
                                     y = 80, 
                                     display=vedit.Display( include_audio=False, display_style=vedit.CROP ) )
    vertical_window = vedit.Window( width=120,
                                    height=214,
                                    x = 740,
                                    y = (640-214)/2, # Center it vertically.
                                    display=vedit.Display( include_audio=False, display_style=vedit.PAN ) )

    # Let's let the system distribute a bunch of our 3 second clips
    # among the horizontal and vertical windows automatically.
    video_clips = []
    for video_file in glob.glob( "./examples/*00[5-9].mp4" ):
        video_clips.append( vedit.Clip( end=3, video=vedit.Video( video_file ) ) )

    # With these options this will randomize the input clips among
    # the two windows, and keep recycling them until the result is 45
    # seconds long.
    vedit.distribute_clips( clips=video_clips, 
                            windows=[ horizontal_window, vertical_window ],
                            min_duration=45,
                            randomize_clips=True )

    # Add the overlay windows to the background.
    dog_background.windows = [ horizontal_window, vertical_window ]

    # Let's set up a watermark image to show over the front and end of
    # out video. The transparent01.png watermark image is 160x160
    # pixels.
    #
    # Let's put it in the top left for the first 10 seconds.
    front_watermark = vedit.Watermark( filename="./examples/transparent01.png",
                                       x=0,
                                       y=0,
                                       fade_out_start=7,
                                       fade_out_duration=3 )
    # Let's put it in the bottom right for the last 15 seconds.
    back_watermark = vedit.Watermark( filename="./examples/transparent01.png",
                                      x=dog_background.width-160,
                                      y=dog_background.height-160,
                                      fade_in_start=-15, # Negative values are times from the end of the video.
                                      fade_in_duration=5 )

    # Add watermarks to the background.
    dog_background.watermarks = [ front_watermark, back_watermark ]

    dog_background.render()
    log.info( "Random clips over static image with watermarks at: %s" % ( output_file ) )


Back to `Table of Contents`_

Module Concepts
================================================================================

Module Concepts

Back to `Table of Contents`_

Display Configuration
--------------------------------------------------------------------------------

Display Configuration

Back to `Table of Contents`_

Windows
--------------------------------------------------------------------------------

Windows

Back to `Table of Contents`_

Videos and Clips
--------------------------------------------------------------------------------

Videos and Clips

Back to `Table of Contents`_

Watermarks
--------------------------------------------------------------------------------

Watermarks

Back to `Table of Contents`_

Audio
--------------------------------------------------------------------------------

Audio

Back to `Table of Contents`_

Logging Output
================================================================================

vedit produces lots of output through Python's logging framework.  Messages are at these levels:

debug
  Everything, including command output from ``ffmpeg``

info
  Step by step notifications of commands run, but curtailing the output
 
warn
  Only notices where vedit is making some determination about what to do with ambiguous inputs

Back to `Table of Contents`_

Getting Help
================================================================================

File an issue on GitHub for this project https://github.com/digitalmacgyver/vedit/issues

Back to `Table of Contents`_

Contributing
================================================================================

Feel free to fork and issue a pull request at: https://github.com/digitalmacgyver/vedit

Back to `Table of Contents`_

Odds and Ends
================================================================================

- The first video stream encountered in a file is the one used, the rest are ignored.
- The first audio stream encountered in a file is the one used, the rest are ignored.
- The output Sample Aspect Ratio (SAR) for a Window can be set.  All inputs and outputs are assumed to have the same SAR.  If not set the SAR of the Video input will be used, or 1:1 will be used if there is no Video input.
- Some video files report strange Sample Aspect Ratio (SAR) via ``ffprobe``. The nonsense SAR value of 0:1 is assumed to be 1:1.  SAR ratios between 0.9 and 1.1 are assumed to be 1:1. 
- The pixel format of the output can be set, the default is yuv420p.
- The output video frame rate will be set to 30000/1001
- The output will be encoded with the H.264 codec.
- The quality of the output video relative to the inputs is set by the ffmpeg -crf option with an argument of 16, which should be visually lossless.
- If all input clips have the same number of audio channels, those channels are in the output.  In any other scenario the resultant video will have a single channel (mono) audio stream.

Back to `Table of Contents`_
