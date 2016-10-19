

Fun utility for combining various video clips with FFMPEG.

For each window, the base most layer will be the bgimage_file (if specified) 

./configure --enable-gpl --enable-libx264 --enable-nonfree --enable-libfdk-aac


Caching behaviors:

* When a Video object is created, ffprobe is called to gather some metadata about the video.  This is done once per unique OS filename per program invocation.  It is not supported to construct different Video objects from the same OS filename but different contents.

    NOTE: Window objects cache data both within and across program
    invocations.  Broadly this saves a ton of compute time by not
    re-transcoding Clips whose results can't change, but can result in
    the wrong stuff if there are collisions in the cache.
    
    If two Clips have the same elements here, they are assumed to be
    the same in the Cache:
    * Absolute path to the filename from the undelying Video object
    * Clip start time
    * Clip end time
    * The dislpay_style of the Clip as being rendered in this Window.
    * Clip width
    * Clip height
    * Window pan_direction (only relevant if display_style is PAN and pan_direction is ALTERNATE)
    * The pixel format of this Window

    If the Cache is incorrect (most likely because the underlying
    contents of an input filename have changed), the cache should be
    cleared by calilng the static clear_cache method of the Window
    class:

    Window.clear_cache()


Video oddities:

* The output Sample Aspect Ratio (SAR) for a Window can be set.  All
  inputs and outputs are assumed to have the same SAR.  If not set the
  SAR of the Video input will be used, or 1:1 will be used if there is
  no Video input.

* Some video files report strange Sample Aspect Ratio (SAR) via ffprobe. The nonsense SAR value of 0:1 is assumed to be 1:1.  SAR ratios between 0.9 and 1.1 are assumed to be 1:1. 

* The pixel format of the output can be set, the default is yuv420p.

* The output video framerate will be set to 30000/1001

* The output will be encoded with the H.264 codec.

* The quality of the output video relative to the inputs is set by the
  ffmpeg -crf option with an argument of 16, which should be visially
  lossless.

* The first video stream encountered in a file is the one used, the rest are ignored.

* The first audio stream encountered in a file is the one used, the rest are ignored.