vedit Overview
==============

vedit is a Python library that simplifies editing and combining video files using ``ffmpeg``.

Examples of the sorts of things vedit makes easy include:

- Extracting a clip from a longer video
- Combining videos or clips together by attaching them end to end
- Composing videos together, for example side by side or overlayed on top of one another
- Changing the resolution of a video and cropping or padding the video
- Overlaying images onto a video
- Adding an audio track (like a song) to a video

These types of tasks should be simple enough with ffmpeg, however in practice there are numerous stumbling blocks. vedit makes the above sorts of video manipulations easy by automatically handling videos with:

- Different resolutions
- Different sample aspect ratios
- Different pixel formats
- Different frame rates
- Different audio streams and channels

Before You Begin
================

vedit depends on the ``ffmpeg`` program from the FFmpeg_ project, and on the libx264 video codec and the libfdk_aac audio codec, for example by configuring ``ffmpeg`` for compilation with:

    ./configure --enable-gpl --enable-libx264 --enable-nonfree --enable-libfdk-aac --enable-libfreetype --enable-libfontconfig

(``--enable-libfreetype --enable-libfontconfig`` only needed if the ``audio_desc`` option is used).

.. _FFmpeg: https://ffmpeg.org/

Table of Contents
=================

- `Examples`_

  - `Example1`_: Clip 2 seconds out of the middle of a video
  - `Example 2`_: Resize a video with PAD, CROP, or PAN
  - `Example 3`_: Put two videos next to each other
  - `Example 4`_: Replace the audio track of a video
  - `Example 5`_: Overlay videos on top of other videos
  - `Example 6`_: Cascade overlayed videos and images on top of a base video or image
  - `Example 7`_: Add an overlay image, such as a watermark

- `Module Concepts`_

  - `Windows`_
  - `Display`_
  - `Videos and Clips`_
  - `Watermarks`_
  - `Audio`_

- `Logging Output`_
- `Getting Help`_
- `Contributing`_
- `Caching Behavior`_
- `Odds and Ends`_

Examples
========

To get an idea of the sorts of things you can do with a few lines of code, consider these examples, which can be generated from the ``examples.py`` script in the root directory of the ``vedit`` Python module.

All the examples below assume that FFmpeg_ is installed as described in `Before You Begin`_.

All the examples below begin with the following boilerplate, and assume the ``./example_output`` directory exists: ::

  #!/usr/bin/env python
  
  import vedit
  import logging
  logging.basicConfig()
  log = logging.getLogger()
  log.setLevel( logging.DEBUG )
   

.. _Example1:


Example 1: Clip 2 seconds out of the middle of a video
---------
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


.. _`Example 2`:
Example 2: Resize a video with PAD, CROP, or PAN
----------
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

.. _`Example 3`:
Example 2: Put two videos next to each other
----------
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

.. _`Example 4`:
Example 4: Replace the audio track of a video
---------
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


.. _`Example 5`:
Example 5: Overlay videos on top of other videos
---------
::

    code


.. _`Example 6`:
Example 6: Cascade overlayed videos and images on top of a base video or image
---------
::

    code


.. _`Example 7`:
Example 7: Add an overlay image, such as a watermark
---------
::

    code


Module Concepts
===============

Module Concepts


Display Configuation
-------

Display Configuration

Windows
-------

Windows

Videos and Clips
----------------

Videos and Clips

Watermarks
----------

Watermarks

Audio
-----

Audio


Logging Output
==============

vedit produces lots of output through Python's logging framework.  Messages are at these levels:

debug
  Everything, including command output from ``ffmpeg``

info
  Step by step notifications of commands run, but curtailing the output
 
warn
  Only notices where vedit is making some determination about what to do with ambiguous inputs

Getting Help
============

File an issue on Github for this project https://github.com/digitalmacgyver/vedit/issues

Contributing
============

Feel free to fork and issue a pull request at: https://github.com/digitalmacgyver/vedit

Caching Behavior
================

When a Video object is created, ``ffprobe`` is called to gather some
metadata about the video.  This is done once per unique OS filename
per program invocation.  It is not supported to construct different
Video objects from the same OS filename but different contents.

Window objects cache data both within and across program
invocations. This saves time by not re-transcoding Clips whose results
can't change, but can result in the wrong output if there are
collisions in the cache.
    
If two Clips have the same elements here, they are assumed to be the
same in the Cache:

- Absolute path to the filename from the undelying Video object
- Clip start time
- Clip end time
- The ``display_style`` of the Display for this Clip as being rendered in this Window.
- Clip width
- Clip height
- Window pan_direction (only relevant if display_style is PAN and pan_direction is ALTERNATE)
- The pixel format of this Window
- The include_audio attribute of the Display for this Clip as it is rendered in this Window

If the Cache is incorrect (most likely because the underlying contents
of an input filename on the filesystem have changed), the cache should
be cleared by calling the static clear_cache method of the Window
class: ``Window.clear_cache()``


Odds and Ends
=============

- The first video stream encountered in a file is the one used, the rest are ignored.
- The first audio stream encountered in a file is the one used, the rest are ignored.
- The output Sample Aspect Ratio (SAR) for a Window can be set.  All inputs and outputs are assumed to have the same SAR.  If not set the SAR of the Video input will be used, or 1:1 will be used if there is no Video input.
- Some video files report strange Sample Aspect Ratio (SAR) via ``ffprobe``. The nonsense SAR value of 0:1 is assumed to be 1:1.  SAR ratios between 0.9 and 1.1 are assumed to be 1:1. 
- The pixel format of the output can be set, the default is yuv420p.
- The output video framerate will be set to 30000/1001
- The output will be encoded with the H.264 codec.
- The quality of the output video relative to the inputs is set by the ffmpeg -crf option with an argument of 16, which should be visually lossless.
- If all input clips have the same number of audio channels, those channels are in the output.  In any other scenario the resultant video will have a single channel (mono) audio stream.
