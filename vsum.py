#!/usr/bin/env python

'''Utility for extracting clips from videos, and composing clips
together into arbitrary nested "windows" in an output.'''

import collections
import commands
import getpass
import glob
import hashlib
import json
import os
import pickle
import random
import re
import shutil
import uuid

################################################################################
################################################################################
################################################################################
# Configuration settings.
################################################################################
################################################################################
################################################################################


# The FFMPEG command to use, this will use whatever is in the path.
#
# This module requires the ffmpeg binary from the FFmpeg project at
# https://ffmpeg.org/
#
# The ffmpeg binary that for a short time was published by the libav
# project is not supported.
#
# If the path where this script is run does not have these binaries,
# the full path to them can be updated here.
#FFMPEG = 'ffmpeg'
#FFPROBE = 'ffprobe'

FFMPEG = '/home/viblio/tmp/ffmpeg_new/ffmpeg/ffmpeg'
FFPROBE = '/home/viblio/tmp/ffmpeg_new/ffmpeg/ffprobe'


# "Constant" Clip display styles.
#
# Do not change these.
#
#
# These DISPLAY_STYPES are used to configure Display objects, which in
# turn define how Clip objects behave when embedded in a Window.
# 
# Each Clip has a pixel width and a height, and each Window has a
# width and a height.
#
# If the Clip and Window do not have identical width and height,
# something must be done to render that Clip within that Window.
# 
# For Clip objects, a DISPLAY_STYLE of:
#
# * CROP - The Clip is scaled in size while preserving its aspect
#          ratio to the smallest size such that both its width and
#          height meet or exceed the width and height of the Window it
#          is placed in. If any portion of the resulting scaled Clip
#          is larger than the Window (which will be the case unless
#          the Clip and Window have the same aspect ratio), the Clip
#          will be cropped.  The center of the Clip will be placed at
#          the center of the Window.
#
# * PAD - The Clip is scaled in size while preserving its aspect ratio
#         to the largest size such that both its width and height are
#         smaller than or equal to the width and height of the window
#         it is placed in.  If the dimensions of the scaled Clip are
#         smaller than the Window (which will be the case unless the
#         Clip and Window have the same aspect ratio), the Clip will
#         be padded onto the solid background of color pad_bgcolor set
#         for the Display object.  The center of the Clip will be
#         placed at the center of the Window.
#
# * PAN - The Clip is scaled in size while preserving its aspect ratio
#         to the smallest size such that both its width and height
#         meet or exceed the width and height of the Window it is
#         placed in.  If any portion of the resulting scaled Clip is
#         larger than the Window (which will be the case unless the
#         Clip and Window have the same aspect ratio), then as the
#         clip plays it will be animated panning to show the entire
#         clip as the clip plays.  The direction the clip is panned
#         depend on whether the Clip is wider than the Window, or
#         taller than the Window, the setting of the Display's
#         pan_direction, and the pan direction of the prior clip in
#         the case that pan_direction was ALTERNATE.
#
# * OVERLAY - If the Display display_style is OVERLAY a complex
#              behavior is created where clips are shrunk down to fill
#              only a part of the window, and then animated to cascade
#              across the window over the duration of their play time.
#              The OVERLAY mode has lots of additional behaviors, in
#              part dictated by he various OVERLAY_DIRECTIONS
OVERLAY   = "overlay"
CROP      = "crop"
PAD       = "pad"
PAN       = "pan"
DISPLAY_STYLES = [ OVERLAY, CROP, PAD, PAN ]

# "Constant" clip overlay and pan values.
#
# Do not change these. 
#
# For the Display display_style of OVERLAY, then DOWN, LEFT, RIGHT, UP
# controls which direction the clip is animated moving over it's
# runtime.
DOWN      = "down"  # Down and right are synonyms for pan directions.
LEFT      = "left"  # Left and up are synonyms for pan directions.
RIGHT     = "right" 
UP        = "up"    
OVERLAY_DIRECTIONS = [ DOWN, LEFT, RIGHT, UP ]

# Constant clip pan values.
#
# Do not change these
#
# For the Display display_style of PAN, then DOWN/RIGHT and or UP/LEFT
# dictate the direction to pan (which of these is in effect depends on
# whether the Clip is wider, or taller, than the Window it is placed
# in.
#
# For the PAN display_style, if the Clip's pan_direction is ALTERNATE,
# then it will pan in the opposite direction of the prior clip than
# panned in the same window.
#
ALTERNATE = "alternate"
PAN_DIRECTIONS = [ ALTERNATE, DOWN, UP ]


################################################################################
################################################################################
################################################################################
# Classes for rendering videos.
################################################################################
################################################################################
################################################################################


################################################################################
class Display( object ):
    '''Display objects allow for the configuration of how a Clip should
    be displayed.

    Whenever a Clip is rendered, it is rendered with the following
    Display settings:
    * If the Clip itself has a Display object, those settings are used.
    * Otherwise, if the Window the Clip is being rendered in has a Display object, those settings are used.
    * Otherwise, the default Display settings are used.

    The default Display settings are:
    * display_style = PAD
    * pad_bgcolor = 'Black'

    The display_style may be set to one of CROP, PAD, PAN, or OVERLAY.

    If display_style is PAD, the pad_bgcolor may be set to any of the
    colors named recognized by the 'ffmpeg -colors' or a RGB code in
    hexadecimal "#RRGGBB" format.

    If display_style is PAN then the pan_direction can bet set to one
    of UP/RIGHT or DOWN/LEFT or ALTERNATE, it defaults to ALTERNATE.

    If display_style is OVERLAY:

    * overlay_direction can be one of LEFT/RIGHT/UP/DOWN and the
      overlay_concurrency may be set.  overlay_concurrency is roughly
      how many clips can be on the screen at the same time during
      overlays.  Defaults to DOWN.

    * overlay_concurrency lists the maximum number of clips that can
      be actively cascading at one time.  Defaults to 3.

    * overlay_min_gap lists the minimum duration between when two
      clips may be started to animate. Defaults to 4 seconds.

    If include_audio is set to true the audio from this clip will be
    included in the output, mixed together with whatever other audio
    is present in concurrent clips.

    NOTE: If overlay_min_gap is high relative to the length of videos,
    there will be times when nothing is cascading and/or there are
    fewer than overlay_concurrency clips cascading.

    '''

    def __init__( self, 
                  display_style       = PAD,
                  pad_bgcolor         = 'Black',
                  overlay_concurrency = 3,
                  overlay_direction   = DOWN,
                  overlay_min_gap     = 4,
                  pan_direction       = ALTERNATE,
                  include_audio       = False ):

        if display_style in DISPLAY_STYLES:
            self.display_style = display_style
        else:
            raise Exception( "Invalid display style: %s, valid display styles are: %s" % ( display_style, DISPLAY_STYLES ) )

        # OVERLAY display_style stuff.
        if overlay_direction in OVERLAY_DIRECTIONS:
            self.overlay_direction = overlay_direction
        else:
            raise Exception( "Invalid overlay direction: %s, valid overlay directions are: %s" % ( overlay_direction, OVERLAY_DIRECTIONS ) )

        self.overlay_concurrency = overlay_concurrency

        self.overlay_min_gap = overlay_min_gap

        # PAN display_style stuff.
        if pan_direction == RIGHT:
            self.pan_direction = DOWN
        elif pan_direction == LEFT:
            self.pan_direction = UP
        elif pan_direction in PAN_DIRECTIONS:
            self.pan_direction = pan_direction
        else:
            raise Exception( "Invalid pan direction: %s, valid pan directions are: %s" % ( pan_direction, PAN_DIRECTIONS ) )

        self.prior_pan = UP
                         
        # PAD display_style stuff.
        self.pad_bgcolor = pad_bgcolor
    
        self.include_audio = include_audio

    # A given Display object alternates the direction of pans when
    # display_type is PAN for each time an object is rendered with it.
    #
    # This is most useful when a Display is associated with a Window,
    # and that Window has multiple Clips and the desire is to
    # alternate pan_directions in that window.
    #
    # It also works for a given Clip, but that would require that
    # single Clip be rendered at least twice in a given context.
    def get_pan_direction( self ):
        if self.pan_direction == ALTERNATE:
            if self.prior_pan == UP:
                self.prior_pan = DOWN
                return DOWN
            else:
                self.prior_pan = UP
                return UP
        else:
            self.prior_pan = self.pan_direction
            return self.pan_direction

################################################################################
class Video( object ):
    '''
    The Video object represents a video associated with a physical file on the filesystem.

    A primary source if Clip objects is to cut them out of Video objects.

    Inputs:
    * Filename - Full OS path to a video file.

    Outputs: None

    '''

    # Class static variable, whenever we get a new Video object we do
    # some FFPROBE calls to find out metadata about that video, but we
    # do it only once filesystem file no matter how many times the
    # object is created.
    #
    # NOTE - it is not supported to invoke Video for different file
    # contents at the same filename over the course of the program.
    videos = {}

    def __init__( self, 
                  filename ):

        if not os.path.exists( filename ):
            raise Exception( "No video found at: %s" % ( filename ) )
        else:
            self.filename = filename

        # Check out static cache of Video data to see if we know about
        # this file already.
        if filename in Video.videos:
            self.width = Video.videos[filename]['width']
            self.height = Video.videos[filename]['height']
            self.duration = Video.videos[filename]['duration']
            self.sample_aspect_ratio = Video.videos[filename]['sample_aspect_ratio']
            self.pix_fmt = Video.videos[filename]['pix_fmt']
            self.channels = Video.videos[filename]['channels']
        else:
            # Collect file metadata with FFPROBE.
            ( status, output ) = commands.getstatusoutput( "%s -v quiet -print_format json -show_format -show_streams %s" % ( FFPROBE, filename ) )
            info = json.loads( output )
            self.duration = float( info['format']['duration'] )
            self.width = int( info['streams'][0]['width'] )
            self.height = int( info['streams'][0]['height'] )
            self.sample_aspect_ratio = info['streams'][0].get( 'sample_aspect_ratio', '' )
            if self.sample_aspect_ratio == '0:1':
                print "WARNING: Nonsense SAR value of 0:1 detected, assuming SAR is 1:1."
                self.sample_aspect_ratio = '1:1'
            else:
                # Deal with weird files with rounding error SARs like 649:639.
                ( sarwidth, sarheight ) = self.sample_aspect_ratio.split( ':' )
                if ( sarwidth != sarheight ) and abs( ( float( sarwidth ) / float( sarheight ) ) - 1 ) < 0.1:
                    print "WARNING: Strange SAR value of %s:%s detected, setting SAR to 1:1." % ( sarwidth, sarheight )
                    self.sample_aspect_ratio = '1:1'
            self.pix_fmt = info['streams'][0].get( 'pix_fmt', '' )

            self.channels = None
            if len( info['streams'] ) > 1:
                if 'channels' in info['streams'][1]:
                    self.channels = int( info['streams'][1]['channels'] )

            Video.videos[filename] = { 'width'    : self.width,
                                       'height'   : self.height,
                                       'duration' : self.duration,
                                       'sample_aspect_ratio' : self.sample_aspect_ratio,
                                       'pix_fmt'  : self.pix_fmt }

################################################################################        
class Clip( object ):
    '''Clip objects represent a segment of a video which will be composed
    with other Clip objects into some Window objects using some
    Display settings and rendered into a result physical video file.

    A Clip is a portion (or all) of a the underlying video represented
    by a Video object.

    Inputs:
    * video - a Video object
    * start - Defaults to 0, the time in seconds this clip begins in
      the source Video
    * end - If specified, the time in seconds this clip ends in the
      source Video, defaults to the end of the Video
    * display - If specified, the Display settings this clip should be
      rendered with.  If not specified this clip will fall back to the
      default Display settings of the Window it is being rendered in.

    '''

    def __init__( self,
                  video               = None,
                  start               = 0,
                  end                 = None,
                  display             = None ):
        if video is None:
            raise Exception( "Clip constructor requires a video argument." )

        self.video = video
        
        self.start = max( float( start ), 0 )
            
        if self.start >= video.duration:
            raise Exception( "Error, asked to start clip at %f but video %s is only %f long." % ( start, video.filename , video.duration ) )

        if end is not None and end > video.duration:
            raise Exception( "Error, asked to end clip at %f but video %s is only %f long." % ( end, video.filename , video.duration ) )

        if end is not None and end <= start:
            raise Exception( "Error, asked to end clip at %f which is less than or equal to the start of %f." % ( end, start ) )

        if end is None:
            self.end = video.duration
        else:
            # Technically this min is unnecessary due to the exception
            # handling above, but it's here to clarify the valid
            # values.
            self.end = min( float( end ), video.duration )

        # It's OK for this to be None.
        self.display = display
            
    def get_duration( self ):
        '''Returns the duration, in seconds, of this Clip.'''
        return self.end - self.start
        
    def get_channels( self ):
        '''Returns the number of channels in the audio for this video, None if there is no audio.'''
        return self.video.channels

    def get_sar( self ):
        '''Returns the Sample Aspect Ratio (SAR) of the Video this Clip is from.'''
        return self.video.sample_aspect_ratio

    def get_pix_fmt( self ):
        '''Returns the Pixel Format of the Video this Clip is from.'''
        return self.video.pix_fmt


######################################################################        
class Window( object ):
    '''Window is the primary object to interact with.

    A Window composes an arbitrary number of other Window and Clip
    objects into a final video (and also maybe some images, sound
    files, watermarks, etc.).  Windows can contain Windows which
    contain Windows etc.

    Constructor arguments:

    * windows - Optional list of other Window objects which are
      children to this Window (may be manipulated after construction
      by explicitly settings the .windows attribute on the returned
      object).

    * clips - Option list of Clip objects to be rendered in this
      Window (may be manipulated after construction by explicitly
      setting the .clips attribute of the returned object).

    * display - An optional Display object to define how Clips should
      be rendered in this window (overridden on a Clip by Clip basis
      of their display argument).  Defaults to the default Display()
      object.

    * force - Defaults to False, force regeneration of all video
      content, ignoring what is in the cache.

    * bgcolor - Defaults to 'Black'.  In a variety of scenarios where
      there is no Clip or image content in a region of a Window, what
      color should that region be.

    * bgimage_file - Defaults to None.  In a variety of scenarios
      where there are no Clips content in a region of the Window, what
      should be shown instead.

    * width - Defaults to 1280.  Width in pixels of this Window.

    * height - Defaults to 720.  Height in pixels of this Window.

    * x - Defaults to 0.  The x coordinate of the top left pixel of
      this Window within its immediate parent Window, if any, as
      measured from the top left.

    * y - Defaults to 0.  The y coordinate of the top left pixel of
      this Window within its immediate parent Window, if any, as
      measured from the top left.

    * audio_filename. Optional.  If specified, an audio track to play
      along with the resultant video.

    * audio_desc.  Optional.  If provided, text to display over the
      end of the video for the last 5 seconds.

    * duration - Optional. If specified the duration of the rendered
      content of this Window.  
  
      Defaults to the length of the optional audio_filename, or if
      that is not provided then defaults to the maximum duration of
      the rendered clips of this or any child windows.  

      The duration of a given set of clips is calculated as the larger
      of:

      + Either, the length of all non-OVERLAY clips concatenated
        together

      + Or the length of the display time of all OVERLAY clips given
        their various staggered start times depending on the number of
        clips, their overlay concurrency, their durations, etc.

      If the specified duration is shorter than the content of clips
      some clips will not be shown.  If it is longer there will be
      blank content at the end of the clips.  

      If the duration and the length of the audio_file differ, then
      the audion file will fade out starting 5 seconds before the end
      of the video.

    * output_file - Defaults to "./output.mp4" where the resulting
      video from a call to render this Window will be created.

    * z_index - Optional.  If there are muliple windows being
      rendered, ones with higher z_indexes are rendered on top of
      others.  If two windows have the same z_index which one ends up
      on top is arbitrary.  If not specified windows will have
      increasing z_index in order of creation.

    * watermarks - Optional.  A list of Watermark image objects to
      overlay on top of the resultant video.

    * sample_aspect_ratio - Optional. The Sample Aspect Ratio (SAR)
      for the rendered content of this Window.  If specified, it must
      be in "W:H" format.  This should not be needed generally unless
      you are encoding for TV broadcast or similar.  Defautls to the
      SAR if the input Video, or 1:1 if there is no input Video.  If
      multiple input videos have different SARs an Exception is
      thrown, you must preprocess your inputs to all have the same
      SAR.

    * pix_fmt - Optional.  The pixel format of this window, defaults
      to yuv420p.  All Windows that are rendered together must have
      the same pix_fmt.

    * overlay_batch_concurrency - Optional.  Defaults to 16.  An
      internal paramter that controls how many overlays we will
      attempt in one command line for FFMPEG.  Increasing this value
      may cause crashes and memory corruption errors, setting it lower
      increases rendering time.

    

    
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

    '''

    # We use z-index to determine what Windows go on top of others.
    # Users can specify their own z_indexes, but if they don't we
    # increment in order of created Window objects.
    z = 0

    tmpdir = '/tmp/vsum/%s/' % ( getpass.getuser() )
    cache_dict_file = 'cachedb'
    cache_dict = {}

    @staticmethod
    def set_tmpdir( tmpdir ):
        if os.path.exists( tmpdir ):
            Window.tmpdir = tmpdir
        else:
            try:
                os.makedirs( tmpdir )
                Window.tmpdir = tmpdir
            except Exception as e:
                raise( "Error creating tmpdir: %s, error was: %s" % ( tmpdir, e ) )

    @staticmethod
    def load_cache_dict():
        '''If a given Clip is reused across several program invocations, we
        save time by not recreating it.  We store information about
        what Clips we have around here.
        '''
        if os.path.exists( "%s/%s" % ( Window.tmpdir, Window.cache_dict_file ) ):
            f = open( "%s/%s" % ( Window.tmpdir, Window.cache_dict_file ), 'r' )
            Window.cache_dict = pickle.load( f )
            f.close()
        else:
            if not os.path.isdir( Window.tmpdir ):
                os.makedirs( Window.tmpdir )
            Window.cache_dict = {}

    @staticmethod
    def save_cache_dict():
        '''If a given Clip is reused across several program invocations, we
        save time by not recreating it.  We store information about
        what Clips we have around here.
        '''
        if not os.path.isdir( Window.tmpdir ):
            os.makedirs( Window.tmpdir )

        f = open( "%s/%s" % ( Window.tmpdir, Window.cache_dict_file ), 'wb' )
        pickle.dump( Window.cache_dict, f )
        f.close()
    
    @staticmethod
    def clear_cache():
        '''Try to remove all the files in the tmpdir.  This is necessary if,
        for example, an input Video filename has new contents.
        '''
        if os.path.isdir( Window.tmpdir ):
            for cache_file in glob.glob( "%s/*" % ( Window.tmpdir ) ):
                try:
                    os.remove( cache_file )
                except Exception as e:
                    raise Exception( "Error while deleting file %s: %s" % ( cache_file, e ) )

    ### Window method ########################################
    def __init__( self,
                  windows = None,
                  clips = None,
                  bgcolor = 'Black',
                  bgimage_file = None, # For windows with no clips, they can optionally place an image on top of their bgcolor.  The image is assumed to be sized correctly, no scaling or placement is done.
                  width = 1280,
                  height = 720,
                  sample_aspect_ratio = None, # If specified, must be
                                              # in W:H format.  Sets
                                              # the sample aspect
                                              # ratio / pixel aspect
                                              # ratio for this window.
                                              # Should not generally
                                              # be used unless
                                              # encoding a video for
                                              # TV broadcast or
                                              # similar.  If not set
                                              # will default to the
                                              # SAR of an input video,
                                              # or 1 if there is no
                                              # input video.  If
                                              # multiple input videos
                                              # have differing SARs an
                                              # exception will be
                                              # issued during
                                              # rendering.
                  pix_fmt = None, # Defaults to yuv420p
                  # The position of this window relative to its parent window (if any)
                  x = 0,
                  y = 0,
                  duration = None, # The total rendered duration,
                                   # defaults to that of the audio
                                   # track if provided, and the
                                   # maximum rendered Clip duration of
                                   # this or any child Window
                                   # objects. Short values may lead to
                                   # some clips never being visible,
                                   # long values may lead to empty
                                   # screen once all clips have been
                                   # shown.
                  z_index = None,
                  watermarks = None,
                  audio_filename = None,
                  audio_desc = '',
                  display = None,
                  output_file = "./output.mp4",
                  overlay_batch_concurrency = 16, # The number of
                                                 # overlays that we
                                                 # will attempt to
                                                 # apply with one
                                                 # command line for
                                                 # FFMPEG - setting
                                                 # this higher may
                                                 # cause crashes and
                                                 # memory corruptions,
                                                 # setting it lower
                                                 # increases rendering
                                                 # time.
                  force = False # If true then we disregard the cache
                                # and regenerate clips each time we
                                # encounter them.
                  ):

        if windows is not None:
            self.windows = windows
        else:
            self.windows = []

        if clips is not None:
            self.clips = clips
        else:
            self.clips = []

        self.bgimage_file = bgimage_file

        self.bgcolor  = bgcolor
        self.width    = width
        self.height   = height

        if sample_aspect_ratio is not None and not re.match( r'\d+:\d+', sample_aspect_ratio ):
            raise Exception( "If sample_aspect_ratio is provided it must be in W:H format." )

        self.sample_aspect_ratio = sample_aspect_ratio
        self.pix_fmt = pix_fmt

        self.x        = x
        self.y        = y


        # If the user doesn't provide z_indexes for this Window, we
        # create them in order that Windows are created.
        if z_index is not None:
            self.z_index = z_index
        else:
            self.z_index = Window.z
            Window.z += 1
        
        if watermarks is not None:
            self.watermarks = watermarks
        else:
            self.watermarks = []

        #self.original_audio = original_audio

        if audio_filename is not None:
            if not os.path.exists( audio_filename ):
                raise Exception( "No audio found at: %s" % ( audio_filename ) )
            else:
                self.audio_filename = audio_filename
                ( status, output ) = commands.getstatusoutput( "%s -v quiet -print_format json -show_format %s" % ( FFPROBE, audio_filename ) )
                audio_info = json.loads( output )
                self.audio_duration = float( audio_info['format']['duration'] )
        else:
            self.audio_filename = None
            self.audio_duration = None

        self.audio_desc = audio_desc

        # Later on, when we render things, duration will get set to
        # the maximum of the rendered Clip durations of this or any
        # child windows unless it has been explicitly set here, or
        # implicitly set here by the audio_duration.
        if duration is None:
            if audio_filename is not None:
                self.duration = self.audio_duration
            else:
                self.duration = duration
        else:
            self.duration = duration


        # Individual Clip objects can override these Dislpay settings.
        if display is not None:
            self.display = display
        else:
            self.display = Display()

        if Window.cache_dict == {}:
            Window.load_cache_dict()

        self.output_file = output_file
        
        self.overlay_batch_concurrency = overlay_batch_concurrency

        self.force = force               
    

    ### Window method ########################################
    def get_display( self, clip ):
        '''Internal utility function to get the Display properties for this
        Clip being rendered in this Window.  The logic is:

        1. If the Clip was created with a Display object, use that.
        2. Otherwise, if the Window was created with a Display object, use that.
        3. Otherwise, use the default Display object.

        '''
        if clip.display is not None:
            return clip.display
        elif self.display is not None:
            return self.display
        else:
            return Display()


    ### Window method ########################################
    def get_next_renderfile( self ):
        '''Internal utility function, we need to generate a bunch of
        intermediate files, this generates unique names for them.

        '''
        return "%s/%s.mp4" % ( Window.tmpdir, str( uuid.uuid4() ) )


    ### Window method ########################################
    def render( self, helper=False ):
        '''If helper is true we're rendering a sub-window, the result of which
        is an intermediate file stored in the tmpdir somewhere.  If
        helper is False then we are rendering user output, and it will
        go in the path specified by self.output_file.

        '''

        # File to accumulate things in.
        tmpfile = None

        child_windows = [ w for w in self.get_child_windows() ]
        all_windows = [ self ] + child_windows

        ###### SAR stuff #####################################
        # Determine the output SAR for this video, or raise an
        # Exception if the inputs have mismatched SARs.
        sars = set( [ clip.get_sar() for window in all_windows if window.sample_aspect_ratio is None for clip in window.clips ] + [ w.sample_aspect_ratio for w in all_windows if w.sample_aspect_ratio is not None ] )
        computed_sar = None
        if len( sars ) > 1:
            raise Exception( "Multiple different sample aspect ratios present in input videos: %s.  Please preprocess your inputs to all have the same SARs." % ( sars ) )
        elif len( sars ) == 1:
            computed_sar = sars.pop()
            
        if self.sample_aspect_ratio is None:
            if computed_sar is not None:
                self.sample_aspect_ratio = computed_sar
        else:
            if computed_sar is not None and computed_sar != self.sample_aspect_ratio:
                # It's OK to mismatch these things, but usually it
                # will be an error that stretches the video by the
                # ratio of the input over the output SAR.
                print "WARNING: input videos/child windows have SAR of %s, but the output SAR of %s has been specified, this may result in distorted output." % ( computed_sar, self.sample_aspect_ratio )

        sar_clause = ""
        if self.sample_aspect_ratio is not None:
            # FFMPEG has deprecated the W:H notation in favor of W/H...
            ( sarwidth, sarheight ) = self.sample_aspect_ratio.split( ':' )
            sar_clause = ",setsar=sar=%s/%s" % ( sarwidth, sarheight )

        ###### Pixel Format stuff #############################
        pix_fmts = set( [ w.pix_fmt for w in all_windows if w.pix_fmt is not None ] )

        computed_pix_fmt = None
        if len( pix_fmts ) > 1:
            raise Exception( "Multiple different color space / pixel format arguments for output windows: %s.  All output windows must have the same pixel format." % ( pix_fmts ) )
        elif len( pix_fmts ) == 1:
            computed_pix_fmt = pix_fmts.pop()
            
        if self.pix_fmt is None and computed_pix_fmt is not None:
            self.pix_fmt = computed_pix_fmt
        else:
            self.pix_fmt = 'yuv420p'
        
        ###### Duration stuff ################################
        if self.duration is None:
            my_duration = max( [ w.compute_duration( w.clips ) for w in all_windows ] )
            if my_duration == 0:
                raise Exception( "Could not determine duration for window." )
            else:
                print "WARNING: No duration specified for window, set duration to %s, the longest duration of clips in this or any of its child windows." % ( my_duration )
                self.duration = my_duration


        #ffmpeg -i VIDEO -i AUDIO -filter_complex "[1:0]apad" -shortest OUTPUT

        ###### Background stuff ##############################
        background_file = self.get_next_renderfile()
        if self.bgimage_file is not None:
            # Lay down a background with silent audio if requested to.
            cmd = '%s -y -loop 1 -i %s -f lavfi -i aevalsrc=0 -c:a libfdk_aac -pix_fmt %s -r 30000/1001 -crf 16 -c:v libx264 -filter_complex " color=%s:size=%dx%d,setpts=PTS-STARTPTS/TB [base] ; [0] setpts=PTS-STARTPTS/TB [image]; [base] [image] overlay%s " -t %f %s' % ( FFMPEG, self.bgimage_file, self.pix_fmt, self.bgcolor, self.width, self.height, sar_clause, self.duration, background_file )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( background_file ):
                raise Exception( "Error producing background image video file %s with command: %s" % ( background_file, cmd ) )
        else:
            # There was no background image, lay down a solid color with silent audio.
            cmd = '%s -y -f lavfi -i aevalsrc=0 -c:a libfdk_aac -pix_fmt %s -r 30000/1001 -crf 16 -c:v libx264  -filter_complex " color=%s:size=%dx%d%s,setpts=PTS-STARTPTS/TB " -t %f %s' % ( FFMPEG, self.pix_fmt, self.bgcolor, self.width, self.height, sar_clause, self.duration, background_file )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( background_file ):
                raise Exception( "Error producing solid background file %s with command: %s" % ( background_file, cmd ) )

        ###### Render This Window's Clips ####################
        tmpfile = self.render_clips( self.clips, background_file )

        ###### Render All Child Windows ######################
        for window in sorted( self.windows, key=lambda x: x.z_index ):
            if window.duration is None:
                window.duration = self.duration
            if window.pix_fmt is None:
                window.pix_fmt = self.pix_fmt

            current = tmpfile
            window_file = window.render( helper=True )
            tmpfile = self.get_next_renderfile()
            
            # WITH AUDIO
            cmd = '%s -y -i %s -i %s -pix_fmt %s -r 30000/1001 -crf 16 -c:v libx264 -c:a libfdk_aac -filter_complex " [0:v] fifo [v0] ; [1:v] fifo [v1] ; [v0] [v1] overlay=x=%s:y=%s:eof_action=pass%s [outv] ; [0:a] afifo [a0] ; [1:a] afifo [a1] ; [a0] [a1] amix=inputs=2:duration=longest:dropout_transition=0 [outa] " -map "[outv]" -map "[outa]" -t %f %s' % ( FFMPEG, current, window_file, window.pix_fmt, window.x, window.y, sar_clause, window.duration, tmpfile )
            # WITHOUT AUDIO
            #cmd = '%s -y -i %s -i %s -pix_fmt %s -r 30000/1001 -crf 16 -c:v libx264  -filter_complex " [0:v] [1:v] overlay=x=%s:y=%s:eof_action=pass%s " -t %f %s' % ( FFMPEG, current, window_file, window.pix_fmt, window.x, window.y, sar_clause, window.duration, tmpfile )

            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( tmpfile ):
                raise Exception( "Error applying overlay window %s to file %s with command: %s" % ( window_file, current, cmd ) )
                
        ###### Render Watermarks #############################
        if len( self.watermarks ) > 0:
            tmpfile = self.add_watermarks( self.watermarks, tmpfile )

        ###### Add Audio and Description #####################
        if self.audio_filename:
            if self.audio_duration is not None and self.audio_duration == self.duration:
                audio_fade_start = self.duration
                audio_fade_duration = 0
            else:
                audio_fade_start = max( 0, self.duration - 5 )
                audio_fade_duration = self.duration - audio_fade_start
            afade_clause = ' -c:a libfdk_aac -af " [1:a] afade=t=out:st=%f:d=%f [a1] ; [0:a] [a1] amix=inputs=2:duration=longest:dropout_transition=0 " ' % ( audio_fade_start, audio_fade_duration )

            current = tmpfile
            tmpfile = self.get_next_renderfile()

            filter_clause = ' -vf copy '

            if self.audio_desc:
                audio_desc_file = '%s/%s.txt' % ( Window.tmpdir, str( uuid.uuid4() ) )
                f = open( audio_desc_file, 'w' )
                f.write( self.audio_desc )
                f.close()
                filter_clause = " -filter_complex 'drawtext=fontcolor=white:borderw=1:textfile=%s:x=10:y=h-th-10:enable=gt(t\,%f)'%s" % ( audio_desc_file, self.duration - 5, sar_clause )

            cmd = '%s -y -i %s -i %s -pix_fmt %s %s %s -t %f %s' % ( FFMPEG, current, self.audio_filename, self.pix_fmt, afade_clause, filter_clause, self.duration, tmpfile )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( tmpfile ):
                raise Exception( "Error adding audio %s to file %s with command: %s" % ( self.audio_filename, current, cmd ) )

        ###### Fix overall volume issues.
        current = tmpfile
        tmpfile = self.get_next_renderfile()
        cmd = '%s -y -i %s -pix_fmt %s -c:a libfdk_aac -vf copy -af " [0:a] dynaudnorm " %s' % ( FFMPEG, current, self.pix_fmt, tmpfile )
        print "Running: %s" % ( cmd )
        ( status, output ) = commands.getstatusoutput( cmd )
        print "Output was: %s" % ( output )
        if status != 0 or not os.path.exists( tmpfile ):
            raise Exception( "Error adjusting volume of file %s with command: %s" % ( current, cmd ) )

        if not helper:
            shutil.copyfile( tmpfile, self.output_file )

        # Render returns the path of the file it generated.
        return tmpfile


    ### Window method ########################################
    def add_watermarks( self, watermarks, current ):
        cmd = '%s -y -i %s ' % ( FFMPEG, current )

        tmpfile = self.get_next_renderfile()

        file_idx = 0

        for watermark in watermarks:
            if watermark.filename is not None:
                file_idx += 1
                cmd += " -loop 1 -i %s " % ( watermark.filename )

        cmd += ' -pix_fmt %s -filter_complex " ' % ( self.pix_fmt )

        filter_idx = 0

        for watermark in watermarks:
            if watermark.bgcolor is not None:
                filter_idx += 1
                cmd += ' color=%s:size=%dx%d [%d] ; ' % ( watermark.bgcolor, watermark.width, watermark.height, file_idx + filter_idx )

        for idx, watermark in enumerate( watermarks ):
            fade_clause = ""
            if watermark.fade_in_start is not None:
                in_start = watermark.fade_in_start
                if in_start < 0:
                    in_start = self.duration + in_start
                in_duration = min( watermark.fade_in_duration, self.duration - in_start )
                fade_clause = "fade=in:st=%f:d=%f" % ( in_start, in_duration )
            if watermark.fade_out_start is not None:
                out_start = watermark.fade_out_start
                if out_start < 0:
                    out_start = self.duration + out_start
                out_duration = min( watermark.fade_out_duration, self.duration - out_start )
                if fade_clause == "":
                    fade_clause = "fade="
                else:
                    fade_clause += ":"
                fade_clause += "out:st=%f:d=%f" % ( out_start, out_duration )

            mark_clause = fade_clause
            if mark_clause == "":
                mark_clause = "copy"

            input_idx = idx+1
            if watermark.filename is None:
                input_idx += file_idx

            cmd += " [%d] %s [w%d] ; " % ( input_idx, mark_clause, idx )

        # Overlay them onto one another
        prior_overlay = '0'
        for idx, watermark in enumerate( watermarks ):
            cmd += ' [%s] [w%d] overlay=x=%s:y=%s:eof_action=pass [o%s] ; ' % ( prior_overlay, idx, watermark.x, watermark.y, idx )
            #cmd += ' [%s] [w%d] overlay=x=%s:y=%s [o%s] ; ' % ( prior_overlay, idx, watermark.x, watermark.y, idx )
            prior_overlay = "o%s" % idx

        #cmd += ' [%s] copy " %s' % ( prior_overlay, tmpfile )

        # Stip off training [o##] ;
        cmd = cmd[:-(6+len( idx-1 ) )]
        cmd += ' " %s' % ( tmpfile )
        print "Running: %s" % ( cmd )
        ( status, output ) = commands.getstatusoutput( cmd )
        print "Output was: %s" % ( output )
        if status != 0 or not os.path.exists( tmpfile ):
            raise Exception( "Error adding watermarks to file %s with command: %s" % ( current, cmd ) )

        return tmpfile


    ### Window method ########################################
    def get_clip_hash( self, clip, width, height, pan_direction="", pix_fmt="yuv420p", include_audio=False ):
        '''It can be very time consuming to produce a clip from a video, we
        endeavor here to not do the same work over and over if it's
        not needed.

        '''

        display = self.get_display( clip )
        clip_name = "%s%s%s%s%s%s%s%s%s" % ( os.path.abspath( clip.video.filename ), 
                                             clip.start, 
                                             clip.end, 
                                             display.display_style, 
                                             width, 
                                             height, 
                                             pan_direction,
                                             pix_fmt,
                                             include_audio )
        md5 = hashlib.md5()
        md5.update( clip_name )
        return md5.hexdigest()


    ### Window method ########################################
    def render_clips( self, clips, background_file ):
        '''Render the clips for the current window.

        Inputs:

        self - The current Window

        clips - a list of clips to render

        background_file - Path to a video file with a background for
        any OVERLAY clips to be rendered onto, this is returned if the
        clips argument is the empty list

        For each clip we:
        
        1. Check in our cache to see if we already have a version of
        this clip in the appropriate resolution.
        
        2. If there is a cache miss, produce a clip of the appropriate
        resolution and cache it.
        
        3. Concatenate and overlay the following clips according to
        this procedure:

        We process the Clips in order in self.clips, and concatenate
        all the non-OVERLAY clips to one another.

        Then we overlay the OVERLAY clips on top, starting at the
        beginning.

        The return value is a file of rendered video, either that
        containing the clips, or just the background_file itself if
        there were no clips.

        '''

        if len( clips ) == 0:
            # Nothing to do.
            return background_file

        tmpfile = None

        clip_files = []
        overlays = []
        
        # Build up our library of clips.
        for clip in self.clips:
            filename = self.clip_render( clip )

            display = self.get_display( clip )
            if display.display_style == OVERLAY:
                overlays.append( { 'clip' : clip,
                                   'filename' : filename } )
            else:
                clip_files.append( filename )
        
        # Concatenate all clip files.
        if len( clip_files ):
            concat_vid = self.get_next_renderfile()
            concat_file = "%s/concat-%s.txt" % ( Window.tmpdir, str( uuid.uuid4() ) )
            f = open( concat_file, 'w' )
            for clip_file in clip_files:
                f.write( "file '%s'\n" % ( clip_file ))
            f.close()

            #if self.original_audio:
            #    cmd = "%s -y -f concat -safe 0 -i %s -pix_fmt %s -r 30000/1001 -crf 16 -c:v libx264  -c:a libfdk_aac %s" % ( FFMPEG, concat_file, self.pix_fmt, concat_vid )
            #else:
            #    cmd = "%s -y -f concat -safe 0 -i %s -pix_fmt %s -r 30000/1001 -crf 16 -c:v libx264  -an %s" % ( FFMPEG, concat_file, self.pix_fmt, concat_vid )

            cmd = "%s -y -f concat -safe 0 -i %s -pix_fmt %s -r 30000/1001 -crf 16 -c:v libx264  -c:a libfdk_aac %s" % ( FFMPEG, concat_file, self.pix_fmt, concat_vid )

            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( concat_vid ):
                raise Exception( "Error producing concatenated file %s with command: %s" % ( concat_vid, cmd ) )

            background_video = Video( background_file )
            overlay_video = Video( concat_vid )

            audio_clause = ""
            if overlay_video.channels is None:
                audio_clause = " [0:a] afifo "
            else:
                audio_clause = " [0:a] afifo [a0] ; [1:a] afifo [a1] ; [a0] [a1] amix=inputs=2:duration=longest:dropout_transition=0 "

            # Put the result on top of the background_file.
            tmpfile = self.get_next_renderfile()
            cmd = '%s -y -i %s -i %s -pix_fmt %s -r 30000/1001 -crf 16 -c:v libx264 -c:a libfdk_aac -filter_complex " [0:v] fifo,setpts=PTS-STARTPTS/TB [a] ; [1:v] fifo,setpts=PTS-STARTPTS/TB [b] ; [a] [b] overlay=x=0:y=0:eof_action=pass ; %s " -t %f %s' % ( FFMPEG, background_file, concat_vid, self.pix_fmt, audio_clause, self.duration, tmpfile )

            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( tmpfile ):
                raise Exception( "Error producing conctenated clip file %s with command: %s" % ( tmpfile, cmd ) )

        else:
            tmpfile = background_file


        # Add our overlays.
        ( duration, overlay_timing ) = self.compute_duration( clips, include_overlay_timing=True )

        # Goofy nested for loops here because ffmpeg has problems if
        # the command line gets too long with too many overlays, so we
        # do it a bit at a time.
        for overlay_group in range( 0, len( overlays ), self.overlay_batch_concurrency ):
            prior_overlay = '0:v'
            cmd = "%s -y -i %s " % ( FFMPEG, tmpfile )
            include_clause = ""
            scale_clause = ""
            filter_complex = ' -pix_fmt %s -r 30000/1001 -crf 16 -c:v libx264  -filter_complex " ' % ( self.pix_fmt )
            audio_clips = []
            for overlay_idx in range( overlay_group, min( len( overlays ), overlay_group + self.overlay_batch_concurrency ) ):
                overlay_start = overlay_timing[overlay_idx][0]
                overlay_end = overlay_timing[overlay_idx][1]
                overlay = overlays[overlay_idx]['clip']
                display = self.get_display( overlay )
                filename = overlays[overlay_idx]['filename']

                include_clause += " -i %s " % ( filename )

                scale = random.uniform( 1.0/3, 2.0/3 )
                # Set the width to be randomly between 2/3 and 1/3th
                # of the window width, and the height so the aspect
                # ratio is retained.
                ow = 2*int( self.width*scale / 2 )
                oh = 2*int( overlay.video.height * ow / ( overlay.video.width * 2 ) )
                ilabel = overlay_idx + 1 - overlay_group
                filter_complex += " [%d:v] fifo,scale=width=%d:height=%d,setpts=PTS-STARTPTS+%f/TB [o%d] ; " % ( ilabel, ow, oh, overlay_start, overlay_idx )
                
                # Only include audio for this clip if the display says to include it.
                if display.include_audio:
                    adelay = overlay_start*1000

                    audio_clips.append( {
                        "ilabel" : ilabel,
                        "start" : adelay,
                        "channels" : overlay.get_channels(),
                    } )

                direction = display.overlay_direction

                if direction in [ UP, DOWN ]:
                    x = random.randint( 0, self.width - ow )
                    if direction == UP:
                        y = "'if( gte(t,%f), H-(t-%f)*%f, NAN)'" % ( overlay_start, overlay_start, float( self.height+oh ) / overlay.get_duration() )
                    elif direction == DOWN:
                        y = "'if( gte(t,%f), -h+(t-%f)*%f, NAN)'" % ( overlay_start, overlay_start, float( self.height+oh ) / overlay.get_duration() )
                else:
                    y = random.randint( 0, self.height - oh )
                    if direction == LEFT:
                        x = "'if( gte(t,%f), -w+(t-%f)*%f, NAN)'" % ( overlay_start, overlay_start, float( self.width+ow ) / overlay.get_duration() )
                    elif direction == RIGHT:
                        x = "'if( gte(t,%f), W-(t-%f)*%f, NAN)'" % ( overlay_start, overlay_start, float( self.width+ow ) / overlay.get_duration() )

                filter_complex += ' [%s] [o%d] overlay=x=%s:y=%s:eof_action=pass [t%d] ; ' % ( prior_overlay, overlay_idx, x, y, overlay_idx )
                #filter_complex += ' [%s] [o%d] overlay=x=%s:y=%s [t%d] ; ' % ( prior_overlay, overlay_idx, x, y, overlay_idx )
                prior_overlay = 't%d' % ( overlay_idx )

            tmpfile = self.get_next_renderfile()                                          
            #cmd += include_clause + filter_complex + ' [t%s] copy " %s' % ( overlay_idx, tmpfile )
            # Strip off the trailing [t##] ; of the filter_complex
            filter_complex = filter_complex[:-(6+len( str( overlay_idx - 1 ) ) )]
            filter_complex += " [outv] ; "
            
            audio_offsets = ""
            audio_mix = " [0:a] "
            aindex = 1
            for aclip in audio_clips:
                adelay_clause = ""
                if aclip['start'] > 0:
                    adelay_clause = ",adelay=" + "|".join( [ str( aclip['start'] ) for x in range( aclip['channels'] ) ] )
                audio_offsets += " [%d:a] afifo%s [a%d] ; " % ( aclip['ilabel'], adelay_clause, aindex )
                audio_mix += " [a%d] " % ( aindex )
                aindex += 1
            if aindex > 1:
                audio_clause = audio_offsets + audio_mix + " amix=inputs=%d:duration=longest:dropout_transition=0 [outa] " % ( aindex )
            else:
                audio_clause = audio_offsets + audio_mix + " afifo [outa] "

            #else:
            #    audio_clause = audio_offsets[:-(6+len( str( aindex ) ) )] + " [outa] "

            filter_complex += audio_clause
            cmd += include_clause + filter_complex + ' " -map "[outv]" -map "[outa]" %s' % ( tmpfile )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( tmpfile ):
                raise Exception( "Error producing clip file by %s at: %s" % ( cmd, tmpfile ) )

        return tmpfile


    ### Window method ########################################
    def clip_render( self, clip ):
        '''Render a single clip into the tmpdir according to the rules defined
        by the appropriate Display object.

        Returns the name of a file where the resulting rendered clip
        is at.
        '''
        display = self.get_display( clip )

        scale_clause = ""
        clip_width = None
        clip_height = None

        if display.display_style == PAD:
            ( scale, ow, oh ) = self.get_output_dimensions( clip.video.width, clip.video.height, self.width, self.height, min )

            clip_width = ow
            clip_height = oh

            xterm = ""
            if ow != self.width:
                xterm = ":x=%d" % ( ( self.width - ow ) / 2 )

            yterm = ""
            if oh != self.height:
                yterm = ":y=%s" % ( ( self.height - oh ) / 2 )

            if scale != 1:
                scale_clause = "scale=width=%d:height=%d," % ( ow, oh )
            
            scale_clause += "pad=width=%d:height=%d%s%s:color=%s" % ( self.width, self.height, xterm, yterm, display.pad_bgcolor )

        elif display.display_style == CROP:
            ( scale, ow, oh ) = self.get_output_dimensions( clip.video.width, clip.video.height, self.width, self.height, max )

            clip_width = ow
            clip_height = oh

            if scale != 1:
                scale_clause = "scale=width=%d:height=%d," % ( ow, oh )
                
            scale_clause += "crop=w=%d:h=%d" % ( self.width, self.height )

        elif display.display_style == PAN:
            ( scale, ow, oh ) = self.get_output_dimensions( clip.video.width, clip.video.height, self.width, self.height, max )

            clip_width = ow
            clip_height = oh

            if scale != 1:
                scale_clause = "scale=width=%d:height=%d," % ( ow, oh )

            # We need to pan the image if scale != 1.
            pan_clause = ''
            if ow > self.width or oh > self.height:
                # Note - we only want to call this if we're actually
                # panning, or it will erroneously trigger us to
                # alternate pan directions.
                direction = display.get_pan_direction() 

                xpan = ''
                if ow  > self.width:
                    xpan = "x=%s" % ( self.get_pan_clause( clip, direction, ow, self.width ) )

                ypan = ''
                if oh  > self.height:
                    ypan = "y=%s" % ( self.get_pan_clause( clip, direction, oh, self.height ) )

                # NOTE: This logic does not allow both x and y
                # panning, additional stuff would be required to get
                # the : separators right in the pan clause if both
                # could be present.
                pan_clause = ":%s%s" % ( xpan, ypan )

            scale_clause += 'crop=w=%d:h=%d%s' % ( self.width, self.height, pan_clause )

        elif display.display_style == OVERLAY:
            # Overlays will be scaled at the time the overlay is
            # applied so we can reuse the same clips at different
            # scales.
            scale_clause = ""

            clip_width = clip.video.width
            clip_height = clip.video.height

        else:
            raise Exception( "Error, unknown display style: %s" % ( display.display_style ) )

        if scale_clause != "":
            scale_clause = ' -filter_complex " %s " ' % ( scale_clause )

        # Now that we have our scale clause, render this thing.
         
        # Check the cache for such a clip.
        # If not, produce it and save it in the cache.
        clip_hash = self.get_clip_hash( clip=clip, 
                                        width=self.width, 
                                        height=self.height, 
                                        pan_direction=display.prior_pan, 
                                        pix_fmt=self.pix_fmt, 
                                        include_audio=display.include_audio ) 

        if clip_hash in Window.cache_dict and not self.force:
            print "Cache hit for clip: %s" % ( clip_hash )
            return Window.cache_dict[clip_hash]
        else:
            filename = "%s/%s.mp4" % ( Window.tmpdir, clip_hash )
            
            #if self.original_audio:
            #    cmd = '%s -y -ss %f -i %s -pix_fmt %s -r 30000/1001 -crf 16 -c:v libx264  -c:a libfdk_aac %s -t %f %s' % ( FFMPEG, clip.start, clip.video.filename, self.pix_fmt, scale_clause, clip.get_duration(), filename )
            #else:
            #    cmd = '%s -y -ss %f -i %s -pix_fmt %s -r 30000/1001 -crf 16 -c:v libx264  -an %s -t %f %s' % ( FFMPEG, clip.start, clip.video.filename, self.pix_fmt, scale_clause, clip.get_duration(), filename )   

            # By default ignore audio.
            audio_arg = " -an "
            if display.include_audio:
                # Include the audio if requested.
                audio_arg = " -c:a libfdk_aac "

            cmd = '%s -y -ss %f -i %s -pix_fmt %s -r 30000/1001 -crf 16 -c:v libx264 %s %s -t %f %s' % ( FFMPEG, clip.start, clip.video.filename, self.pix_fmt, audio_arg, scale_clause, clip.get_duration(), filename )
            
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status == 0 and os.path.exists( filename ):
                Window.cache_dict[clip_hash] = filename
                Window.save_cache_dict()
            else:
                raise Exception( "Error producing clip file by %s at: %s" % ( cmd, filename ) )

        return filename


    ### Window method ########################################
    def get_pan_clause( self, clip, direction, c, w ):
        duration = clip.get_duration()
        pan_clause = ''
        if c  > w:
            pixels_per_sec = float( ( c - w ) ) / duration
            if direction in [ DOWN, RIGHT ]:
                pan_clause = "trunc(%f * t)" % ( pixels_per_sec )
            elif direction in [ UP, LEFT ]:
                pan_clause = "%d-trunc(%f * t)" % ( c - w, pixels_per_sec )
            else:
                raise Exception( "Could not determine pan direction." )
            
        return pan_clause


    ### Window method ########################################
    def get_output_dimensions( self, cw, ch, ww, wh, operator ):
        scale = operator( float( ww ) / cw, float( wh ) / ch )
        ow = int( cw * scale )
        oh = int( ch * scale )
        
        # If we are very near the aspect ratio of the target
        # window snap to that ratio.
        if ( ow > ww - 2 ) and ( ow < ww + 2 ):
            ow = ww
        if ( oh > wh - 2 ) and ( oh < wh + 2 ):
            oh = wh
            
        # If we have an odd size add 1.
        if ow % 2:
            ow += 1
        if oh %2:
            oh += 1

        return ( scale, ow, oh )


    ### Window method ########################################
    def compute_duration( self, clips, include_overlay_timing=False ):
        '''Don't actually do anything, just report how long the clips will
        take to render in this window.
        
        Returns either a float (if include_overlay_timing is false), or
        a tuple with the float and an array of overlay timing data.

        The array of timing data has N elements, one for each clip of
        type Overlay, and each element is a start time, end time
        tuple.

        The logic is:

        Clips whose display_type is not OVERLAY are appended to one
        another.

        Clips whose display_type is OVERLAY cascade on top of those as
        dictated by the number of them, their durations, and the
        overlay_concurrency and overlay_min_gap their Displays have.

        '''

        # Compute the duration due to non-OVERLAY Clips.
        serial_start = 0
        duration = 0
        for clip in clips:
            display = self.get_display( clip )

            if display.display_style != OVERLAY:
                serial_start += clip.get_duration()
                duration += clip.get_duration()


        # Compute any change to the duration based on OVERLAY Clips,
        # and also compute the overlay timing data structure.
        overlay_start = 0
        overlay_timing = []
        overlay_prior_start = 0
        for clip in clips:
            display = self.get_display( clip )

            if display.display_style == OVERLAY:
                # Initially we spin up to display.overlay_concurrency
                # clips going, one immediately and the rest followed
                # at display.overlay_min_gap intervals, we do this
                # until there could be more than
                # display.overlay_concurrency videos going at once.
                if len( overlay_timing ) < display.overlay_concurrency:
                    overlay_start = len( overlay_timing ) * display.overlay_min_gap

                    overlay_end = overlay_start + clip.get_duration()

                    # If we have more overlays than non-overlays, update duration accordingly.
                    if overlay_end > duration:
                        duration = overlay_end

                    overlay_timing.append( ( overlay_start, overlay_end ) )

                    # Set the value for the next iteration.
                    overlay_prior_start = overlay_start

                else:
                    # Find the earliest time one of the most recently
                    # started overlay_concurrency clips are ending,
                    # this is our candidate for when to start the next
                    # clip.
                    overlay_start = min( sorted( [ x[1] for x in overlay_timing ] )[-display.overlay_concurrency:] )

                    if overlay_start - overlay_prior_start < display.overlay_min_gap:
                        # If not enough time has elapsed since we
                        # started a clip, push it out a bit.
                        overlay_start = overlay_prior_start + display.overlay_min_gap

                    overlay_end = overlay_start + clip.get_duration()
                        
                    overlay_timing.append( ( overlay_start, overlay_end ) )

                    # If we have more overlays than non-overlays, update duration accordingly.
                    if overlay_end > duration:
                        duration = overlay_end

                    # Set the value for the next iteration.
                    overlay_prior_start = overlay_start

        if include_overlay_timing:
            return ( duration, overlay_timing )
        else:
            return duration


    ### Window method ########################################
    def get_child_windows( self, include_self=False ):
        '''Recursively get the list of all child windows.'''

        def flatten( l ):
            '''Internal only helper function for collapsing all nested window
            objects onto a single list.'''

            for el in l:
                if isinstance( el, collections.Iterable ) and not isinstance( el, basestring ):
                    for sub in flatten( el ):
                        yield sub
                else:
                    yield el

        prepend = []
        if include_self:
            prepend = [ self ]
        return flatten( prepend + [ w.get_child_windows( include_self=True ) for w in self.windows ] )


# Note - I had intended to offer scale arguments for watermark, but
# ran across FFMPEG bugs (segmentation faults, memory corruption) when
# using the FFMPEG scale filter on PNG images, so I left it out.
class Watermark( object ):
    def __init__( self, 
                  filename = None,
                  x = "0",
                  y = "0",
                  fade_in_start = None,     # Negative values are taken relative to the end of the video
                  fade_in_duration = None,
                  fade_out_start = None,    # Negative values are taken relative to end of video.
                  fade_out_duration = None,
                  bgcolor = None,
                  width = None,
                  height = None ):

        self.filename = filename
        if filename is not None and not os.path.exists( filename ):
            raise Exception( "No watermark media found at: %s" % ( filename ) )
        
        self.bgcolor = bgcolor
        self.width = width
        self.height = height

        if self.filename is None and ( self.bgcolor is None or self.width is None or self.height is None ):
            raise Exception( "Either filename, or all of bgcolor, width, and height must be provided." )
        elif self.filename is not None and ( self.bgcolor is not None ):
            raise Exception( "Can't specify both filename and bgcolor for watermark." )

        self.x = x
        self.y = y
        self.fade_in_start = fade_in_start
        self.fade_in_duration = fade_in_duration
        self.fade_out_start = fade_out_start
        self.fade_out_duration = fade_out_duration



######################################################################
######################################################################
######################################################################
# UTILITY METHODS
######################################################################
######################################################################
######################################################################

######################################################################
def distribute_clips( clips, windows, min_duration=None, randomize_clips=False ):
    '''Utility function for creating collage videos of a set of clips.

    Input/Output parameters: 

    * windows - A list of vsum.Window objects to distribute the clips
      among.  These Window objects are modified by having whatever
      clips this function determines to send to them added to the end
      of their clips list.

    Inputs:
    * clips - A list of vsum.Clip objects to distribute

    * min_duration - If set to a numeric value the clips will be
      repeated over and over until the desired min_duration is met.
      Otherwise each clip is shown once and the resulting duration is
      a function of the resulting length within each window.
      
    NOTE: If min_duration is set, once it is obtained no more clips
    will be added to the result, and some input clips may be unused
    in that scenario.

    * randomize_clips - If true the input clips array will have it's
      contents randomized prior to being distributed, otherwise the
      resulting clips will be shown in order.

    The main idea is that a set of "windows" will be defined, such as
    this:

    +------------------------------------------+
    |                  Window 1                |
    |  +-------------------------+             |
    |  | Window 2                |  +---------+|
    |  |                         |  | Window 3||
    |  +-------------------------+  |         ||
    |                               |         ||
    |                               |         ||
    |                               +---------+|
    +------------------------------------------+

    And clips will be distributed among them.

    This attempts to place clips in the window whose aspect ratio is a
    close match for the clip, while also balancing the total content
    duration of the clips in the windows (note: this can be different
    from the total duration of the rendered window when cascading
    clips are used).

    The exact logic used to distribute clips is:

    1. Get a prioritize list of windows to put the clip in, the
    windows are prioritized first by having the closest aspect ratio
    to the clip, and then among windows with the same aspect ratio
    from lowest window duration to longest.

    2. Then, we walk down this prioritized list and place this clip in
    the first window such that both:
        * ( window_duration + clip_duration ) <= 1.2*( minimum_window_duration + clip_duration )
        * and, if min_duration is set:
        * window_duration < min_duration

    '''

    if len( clips ) == 0:
        return

    window_stats = []
    for window in windows:
        ar = float( window.width ) / window.height
        duration = 0
        window_stats.append( { 'window'   : window,
                               'ar'       : ar,
                               'duration' : duration } )

    # Internal only function to do the recursive work of parseling out
    # things.
    def add_clips_helper():
        if randomize_clips:
            random.shuffle( clips )

        for clip in clips:
            ar = float( clip.video.width ) / clip.video.height
            duration = clip.get_duration()

            window_durations = [ x.compute_duration( x.clips ) for x in windows ]
            min_window_duration = min( window_durations )

            # Sort candidate windows by increasing AR match and then by increasing duration.
            window_stats.sort( key=lambda x: ( abs( x['ar'] - ar ), x['duration'] ) )
        
            # Find a window to add this clip to, while maintaining this
            # constraint:
            #
            # Find the first window sorted by closest aspect ratio and
            # then duration so long as adding this clip to the window so
            # long as:
            # window.duration + clip.duration <= 1.2*(min_window_duration + clip.duration)
            # window.duration < min_duration (if min_duration is not none)
            clip_added = False
            for window in window_stats:
                if ( window['duration'] + duration ) <= 1.2*( min_window_duration + duration ):
                    if min_duration is None or window['duration'] < min_duration:
                        window['window'].clips.append( clip )
                        window['duration'] = window['window'].compute_duration( window['window'].clips )
                        clip_added = True
                        break
                  
            if not clip_added and min_duration is None:
                raise Exception( "Failed to place clip in a window." )

    if min_duration is None:
        add_clips_helper()
    else:
        add_clips_helper()
        window_durations = [ x.compute_duration( x.clips ) for x in windows ]
        while min( window_durations ) < min_duration:
            add_clips_helper()
            window_durations = [ x.compute_duration( x.clips ) for x in windows ]

    # No return value - the windows input/output parameter has the
    # chances made by this routine.
    return

################################################################################
def get_solid_clip( duration,
                    width   = 1280,
                    height  = 720,
                    bgcolor = 'Black',
                    bgimage_file = None,
                    output_file = None ):
    '''Create a video file of the desired properties.

    Inputs:
    * duration - Time in seconds of the video
    * width / height - Width / height in pixels of the video.
    * bgcolor - The background color of the video
    * bgimage_file - Optional, if specified the video should consist
      of this image rather than a solid color.

    * output_file - If specified, the resulting file will be placed at
      output_file.  Default is to place it in the vsum module's
      temporary files location, which is by default

    Outputs: Returns a string denoting the filesystem path where the
    resulting video can be found.

    '''
    
    #ffmpeg -f lavfi -i aevalsrc=0 -i video.mov -shortest -c:v copy -c:a aac \
    #                              -strict experimental output.mov
    #ffmpeg -f lavfi -i aevalsrc=0:0:0:0:0:0::duration=1 silence.ac3


    w = Window( duration = duration,
                width    = width,
                height   = height,
                bgcolor  = bgcolor,
                bgimage_file = bgimage_file )
    
    return w.render()

if __name__ == '__main__':
    ''' Example usage:
    # Set some display properties.
    d = Display( display_style = PAN )

    # If the cache might be bad, we can clean it out.
    Window.clear_cache()

    # Define some videos.
    v1 = Video( 'test.mp4' )
    v2 = Video( 'flip.mp4' )    

    # Define some clips from our videos.
    c1 = Clip( v1, 1, 3 )  
    c2 = Clip( v1, 7, 8 )
    c3 = Clip( v2, 5, 6 )
    cx = Clip( v1, 4, 9 )
    c4 = Clip( v1, 4, 9, display=Display( display_style=OVERLAY, overlay_direction = UP ) )
    c5 = Clip( v2, 0, 1, display=Display( display_style=OVERLAY, overlay_direction = DOWN ) )
    c6 = Clip( v2, 1, 2, display=Display( display_style=OVERLAY, overlay_direction = LEFT ) )
    c7 = Clip( v2, 2, 3, display=Display( display_style=OVERLAY, overlay_direction = RIGHT ) )
    c8 = Clip( v2, 3, 5 )

    # Define some windows.
    w0 = Window( width=1280, height=1024, audio_filename='/wintmp/music/human405.m4a', duration=10 )
    w1 = Window( display = d, height=1024, width=720 )
    w2 = Window( width=200, height=200, x=520, y=520 )
    w3 = Window( display=Display( display_style=OVERLAY, overlay_direction=RIGHT ), bgcolor='White', width=560, height=512, x=720 )
    w4 = Window( display=Display( display_style=PAD, overlay_direction=RIGHT, pad_bgcolor='Green' ), bgcolor='Green', width=560, height=512, x=720, y=512 )

    # We can apply some static image watermarks.
    m1 = Watermark( '/wintmp/summary-test/logo.png',
                    x = "main_w-overlay_w-10",
                    y = "main_h-overlay_h-10",
                    fade_out_start = 3,
                    fade_out_duration = 1 )
    m2 = Watermark( '/wintmp/summary-test/logo128.png',
                    x = "trunc((main_w-overlay_w)/2)",
                    y = "trunc((main_h-overlay_h)/2)",
                    fade_in_start = -1,
                    fade_in_duration = 1 )
    w0.watermarks = [ m1, m2 ]

    # Windows can hold clips and/or other windows.
    w0.windows = [ w1, w3, w4 ]
    # We can even have windows holding windows, e.g. w0->w1->w2.
    w1.windows = [ w2 ]

    # Manually assign clips to windows.
    w2.clips = [ c3 ]
    w1.clips = [ c1, c2 ]
    w3.clips = [ c4, c5, c6, c7, c8 ]
    w0.output_file = 'output1.mp4'
    w0.render()

    # Automatically distribute clips among windows..
    distribute_clips( [ c1, c2, c3, c8, cx, c4, c5, c6, c7 ], [ w1, w2, w3, w4 ], w0.duration )
    w0.output_file = 'output2.mp4'
    w0.render()
    '''
    pass
    
        
