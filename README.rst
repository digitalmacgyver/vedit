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

    ./configure --enable-gpl --enable-libx264 --enable-nonfree --enable-libfdk-aac

.. _FFmpeg: https://ffmpeg.org/

Table of Contents
=================

- `Examples`_

  - `Example 1`_: Clip 2 seconds out of the middle of a video 

- `Logging Output`_
- `Getting Help`_
- `Contributing`_
- `Caching Behavior`_
- `Odds and Ends`_

Examples
========

All the examples below assume that FFmpeg_ is installed as described in `Before You Begin`_.

All the examples below begin with the following boilerplate: ::

  #!/usr/bin/env python
  
  import vedit
  import logging
  logging.basicConfig()
  log = logging.getLogger()
  log.setLevel( logging.DEBUG )
   

Example 1: Clip 2 seconds out of the middle of a video
---------
.. _`Example 1`:

Example 1



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
- The dislpay_style of the Display for this Clip as being rendered in this Window.
- Clip width
- Clip height
- Window pan_direction (only relevant if display_style is PAN and pan_direction is ALTERNATE)
- The pixel format of this Window
- The include_audio attribute of the Display for this Clip as it is rendered in this Window

If the Cache is incorrect (most likely because the underlying contents
of an input filename on the filesystem have changed), the cache should
be cleared by calilng the static clear_cache method of the Window
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
- The quality of the output video relative to the inputs is set by the ffmpeg -crf option with an argument of 16, which should be visially lossless.
- If all input clips have the same number of auido channels, those channels are in the output.  In any other scenario the resultant video will have a single channel (mono) audio stream.
