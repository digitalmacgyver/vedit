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
FFMPEG = 'ffmpeg'
FFPROBE = 'ffprobe'

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
# something must be done to rander that Clip within that Window.
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
#         smaller than the Window (whicih will be the case unless the
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
#         the case that pan_direction was ALTERANTE.
#
# * OVERLAY - If the Display display_style is OVERLAY a comlpex
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
    of UP/RIGHT or DOWND/LEFT or ALTERNATE, it defaults to ALTERNATE.

    If display_style is OVERLAY:

    * overlay_direction can be one of LEFT/RIGHT/UP/DOWN and the
      overlay_concurrency may be set.  overlay_concurrency is roughly
      how many clips can be on the screen at the same time during
      overlays.  Defaults to DOWN.

    * overlay_concurrency lists the maximum number of clips that can
      be actively cascading at one time.  Defaults to 3.

    * overlay_min_gap lists the minimum duration between when two
      clips may be started to animate. Defaults to 4 seconds.

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
                  pan_direction       = ALTERNATE ):

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
    
    # A given Display object alternates the direction of pans when
    # display_type is PAN for each time an object is rendered with it.
    #
    # This is most useful when a Display is associated with a Window,
    # and that Window has multiple Clips and the desire is to
    # alternate pan_directions in that window.
    #
    # It also works for a given Clip, but that would require that
    # sigle Clip be rendered at least twice in a given context.
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
    * width - 

    '''

    # Class static variable, whenever we get a new Video object we do
    # some FFPROBE calls to find out meadata about that video, but we
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
        else:
            # Collect file metadata with FFPRBE.
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
    * display - If specified, the Display settinsg this clip should be
      rendered with.  If not specified this clip will fall back to the
      default Display settings of the Window it is being rendered in.

    '''

    def __init__( self,
                  video               = None,
                  start               = 0,
                  end                 = None,
                  display             = None ):
        if video is None:
            raise Exception( "Clip consturctor requires a video argument." )

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
            # Technically this min is unecessary due to the exception
            # handling above, but it's here to clarify the valid
            # values.
            self.end = min( float( end ), video.duration )

        # It's OK for this to be None.
        self.display = display
            
    def get_duration( self ):
        '''Returns the duration, in seconds, of this Clip.'''
        return self.end - self.start
        
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
    files, watermarks, etc.)

    '''
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
                raise( "Error creting tmpdir: %s, error was: %s" % ( tmpdir, e ) )

    @staticmethod
    def load_cache_dict():
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
        if not os.path.isdir( Window.tmpdir ):
            os.makedirs( Window.tmpdir )

        f = open( "%s/%s" % ( Window.tmpdir, Window.cache_dict_file ), 'wb' )
        pickle.dump( Window.cache_dict, f )
        f.close()
    
    @staticmethod
    def clear_cache():
        if os.path.isdir( Window.tmpdir ):
            for cache_file in glob.glob( "%s/*" % ( Window.tmpdir ) ):
                try:
                    os.remove( cache_file )
                except Exception as e:
                    raise Exception( "Error while deleting file %s: %s" % ( cache_file, e ) )

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
                                   # track. Short values may lead to
                                   # some clips never being visible,
                                   # long values may lead to empty
                                   # screen once all clips have been
                                   # shown.
                  z_index = None,
                  watermarks = None,
                  original_audio = False,
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

        if z_index is not None:
            self.z_index = z_index
        else:
            self.z_index = Window.z
            Window.z += 1
        
        if watermarks is not None:
            self.watermarks = watermarks
        else:
            self.watermarks = []

        self.original_audio = original_audio

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

        if duration is None:
            if audio_filename is not None:
                self.duration = self.audio_duration
            else:
                self.duration = duration
        else:
            self.duration = duration

        if display is not None:
            self.display = display
        else:
            self.display = Display()

        if Window.cache_dict == {}:
            Window.load_cache_dict()

        self.output_file = output_file
        
        self.overlay_batch_concurrency = overlay_batch_concurrency

        self.force = force               
    
    def get_display( self, clip ):
        if clip.display is not None:
            return clip.display
        elif self.display is not None:
            return self.display
        else:
            return Display()

    def get_next_renderfile( self ):
        return "%s/%s.mp4" % ( Window.tmpdir, str( uuid.uuid4() ) )

    def render( self, helper=False ):
        # File to accumulate things in.
        tmpfile = None

        child_windows = [ w for w in self.get_child_windows() ]
        all_windows = [ self ] + child_windows
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
                print "WARNING: input videos/child windows have SAR of %s, but the output SAR of %s has been specified, this may result in distorted output." % ( computed_sar, self.sample_aspect_ratio )

        sar_clause = ""
        if self.sample_aspect_ratio is not None:
            # FFMPEG has deprecated the W:H notation in favor of W/H...
            ( sarwidth, sarheight ) = self.sample_aspect_ratio.split( ':' )
            sar_clause = ",setsar=sar=%s/%s" % ( sarwidth, sarheight )

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

        if self.duration is None:
            my_duration = max( [ w.compute_duration( w.clips ) for w in all_windows ] )
            if my_duration == 0:
                raise Exception( "Could not determine duration for window." )
            else:
                print "WARNING: No duration specified for window, set duration to %s, the longest duration of clips in this or any of its child windows." % ( my_duration )
                self.duration = my_duration

        # Lay down a background if requested to.
        if self.bgimage_file is not None:
            tmpfile = self.get_next_renderfile()
            cmd = '%s -y -loop 1 -i %s -pix_fmt %s -r 30000/1001 -qp 18 -filter_complex " color=%s:size=%dx%d [base] ; [base] [0] overlay%s " -t %f %s' % ( FFMPEG, self.bgimage_file, self.pix_fmt, self.bgcolor, self.width, self.height, sar_clause, self.duration, tmpfile )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( tmpfile ):
                raise Exception( "Error producing solid background file %s with command: %s" % ( tmpfile, cmd ) )

        # Handle the case where there are no clips and no background.
        if len( self.clips ) == 0 and self.bgimage_file is None:
            tmpfile = self.get_next_renderfile()
            cmd = '%s -y -pix_fmt %s -r 30000/1001 -qp 18 -filter_complex " color=%s:size=%dx%d%s " -t %f %s' % ( FFMPEG, self.pix_fmt, self.bgcolor, self.width, self.height, sar_clause, self.duration, tmpfile )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( tmpfile ):
                raise Exception( "Error producing solid background file %s with command: %s" % ( tmpfile, cmd ) )
        else:
            tmpfile = self.render_clips( self.clips, tmpfile )

        for window in sorted( self.windows, key=lambda x: x.z_index ):
            if window.duration is None:
                window.duration = self.duration
            if window.pix_fmt is None:
                window.pix_fmt = self.pix_fmt
            current = tmpfile
            window_file = window.render( helper=True )
            tmpfile = self.get_next_renderfile()
            
            # WITH AUDIO
            #cmd = '%s -y -i %s -i %s -pix_fmt %s -r 30000/1001 -qp 18 -filter_complex " [0:v] [1:v] overlay=x=%s:y=%s:eof_action=pass%s " -a:c libfdk_aac -t %f %s' % ( FFMPEG, current, window_file, self.pix_fmt, window.x, window.y, sar_clause, self.duration, tmpfile )
            # WITHOUT AUDIO
            cmd = '%s -y -i %s -i %s -pix_fmt %s -r 30000/1001 -qp 18 -filter_complex " [0:v] [1:v] overlay=x=%s:y=%s:eof_action=pass%s " -t %f %s' % ( FFMPEG, current, window_file, self.pix_fmt, window.x, window.y, sar_clause, self.duration, tmpfile )
            #cmd = '%s -y -i %s -i %s -r 30000/1001 -qp 18 -filter_complex " [0:v] [1:v] overlay=x=%s:y=%s " -t %f %s' % ( FFMPEG, current, window_file, window.x, window.y, self.duration, tmpfile )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( tmpfile ):
                raise Exception( "Error applying overlay window %s to file %s with command: %s" % ( window_file, current, cmd ) )

        if len( self.watermarks ) > 0:
            tmpfile = self.add_watermarks( self.watermarks, tmpfile )

        if self.audio_filename:
            if self.audio_duration is not None and self.audio_duration == self.duration:
                audio_fade_start = self.duration
                audio_fade_duration = 0
            else:
                audio_fade_start = max( 0, self.duration - 5 )
                audio_fade_duration = self.duration - audio_fade_start
            afade_clause = ' -c:a libfdk_aac -af "afade=t=out:st=%f:d=%f" ' % ( audio_fade_start, audio_fade_duration )
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

        # DEBUG - here it would be nice to detect if the thing had an
        # audio stream and/or respond to command line arguments to
        # that effect.

        if not helper:
            shutil.copyfile( tmpfile, self.output_file )
        return tmpfile

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

        cmd += ' [%s] copy " %s' % ( prior_overlay, tmpfile )
        print "Running: %s" % ( cmd )
        ( status, output ) = commands.getstatusoutput( cmd )
        print "Output was: %s" % ( output )
        if status != 0 or not os.path.exists( tmpfile ):
            raise Exception( "Error adding watermarks to file %s with command: %s" % ( current, cmd ) )

        return tmpfile

    def get_clip_hash( self, clip, width, height, pan_direction="", pix_fmt="yuv420p" ):
        display = self.get_display( clip )
        clip_name = "%s%s%s%s%s%s%s%s" % ( os.path.abspath( clip.video.filename ), 
                                           clip.start, 
                                           clip.end, 
                                           display.display_style, 
                                           width, 
                                           height, 
                                           pan_direction,
                                           pix_fmt )
        md5 = hashlib.md5()
        md5.update( clip_name )
        return md5.hexdigest()

    def render_clips( self, clips, tmpfile ):
        # For each clip we:
        #
        # 1. Check in our cache to see if we already have a version of
        # this clip in the appropriate resolution.
        #
        # 2. If there is a cache miss, produce a clip of the
        # appropriate resolution and cache it.
        #
        # 3. Concatenate all the resulting clips.

        if len( clips ) == 0:
            # Nothing to do.
            return tmpfile

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
            tmpfile = self.get_next_renderfile()
            concat_file = "%s/concat-%s.txt" % ( Window.tmpdir, str( uuid.uuid4() ) )
            f = open( concat_file, 'w' )
            for clip_file in clip_files:
                f.write( "file '%s'\n" % ( clip_file ))
            f.close()
            if self.original_audio:
                cmd = "%s -y -f concat -i %s -pix_fmt %s -r 30000/1001 -qp 18 -c:a libfdk_aac %s" % ( FFMPEG, concat_file, self.pix_fmt, tmpfile )
            else:
                cmd = "%s -y -f concat -i %s -pix_fmt %s -r 30000/1001 -qp 18 -an %s" % ( FFMPEG, concat_file, self.pix_fmt, tmpfile )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( tmpfile ):
                raise Exception( "Error producing concatenated file %s with command: %s" % ( tmpfile, cmd ) )
        elif tmpfile is None:
            # All the clips are overlays and we have no background.
            duration = self.compute_duration( self.clips )
            tmpfile = self.get_next_renderfile()
            cmd = '%s -y -pix_fmt %s -r 30000/1001 -qp 18 -filter_complex " color=%s:size=%dx%d " -t %f %s' % ( FFMPEG, self.pix_fmt, self.bgcolor, self.width, self.height, duration, tmpfile )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( tmpfile ):
                raise Exception( "Error producing solid background file %s with command: %s" % ( tmpfile, cmd ) )   

        # Add our overlays.

        ( duration, overlay_timing ) = self.compute_duration( clips, include_overlay_timing=True )

        # DEBUG
        # THIS IS A HACK TO ACCOMODATE A SINGLE UNDERLYING BASE CLIP.
        #overlay_mod = - ( self.compute_duration( [ clips[0] ] ) - 8 )
        #overlay_timing = [ ( x[0] + overlay_mod, x[1] + overlay_mod ) for x in overlay_timing ]
        # BRUTAL HACK TO GET THE FIRST CLIP TO DO WHAT I WANT!!!
        #overlay_timing[0] = ( 3, 18 )

        for overlay_group in range( 0, len( overlays ), self.overlay_batch_concurrency ):
            prior_overlay = '0:v'
            cmd = "%s -y -i %s " % ( FFMPEG, tmpfile )
            include_clause = ""
            scale_clause = ""
            filter_complex = ' -pix_fmt %s -r 30001/1001 -qp 18 -filter_complex " ' % ( self.pix_fmt )
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
                filter_complex += " [%d:v] scale=width=%d:height=%d,setpts=PTS-STARTPTS+%f/TB [o%d] ; " % ( ilabel, ow, oh, overlay_start, overlay_idx )

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

                #filter_complex += ' [%s] [o%d] overlay=x=%s:y=%s:eof_action=pass [t%d] ; ' % ( prior_overlay, overlay_idx, x, y, overlay_idx )
                filter_complex += ' [%s] [o%d] overlay=x=%s:y=%s [t%d] ; ' % ( prior_overlay, overlay_idx, x, y, overlay_idx )
                prior_overlay = 't%d' % ( overlay_idx )

            tmpfile = self.get_next_renderfile()                                          
            cmd += include_clause + filter_complex + ' [t%s] copy " %s' % ( overlay_idx, tmpfile )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( filename ):
                raise Exception( "Error producing clip file by %s at: %s" % ( cmd, filename ) )

        return tmpfile

    def clip_render( self, clip ):
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
                # the : seperators right in the pan clause if both
                # could be present.
                pan_clause = ":%s%s" % ( xpan, ypan )

            scale_clause += 'crop=w=%d:h=%d%s' % ( self.width, self.height, pan_clause )

        elif display.display_style == OVERLAY:
            # Ovarlays will be scaled at the time the overlay is
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
        clip_hash = self.get_clip_hash( clip, self.width, self.height, display.prior_pan, self.pix_fmt ) 
        if clip_hash in Window.cache_dict and not self.force:
            print "Cache hit for clip: %s" % ( clip_hash )
            return Window.cache_dict[clip_hash]
        else:
            filename = "%s/%s.mp4" % ( Window.tmpdir, clip_hash )
            
            if self.original_audio:
                cmd = '%s -y -ss %f -i %s -pix_fmt %s -r 30000/1001 -qp 18 -c:a libfdk_aac %s -t %f %s' % ( FFMPEG, clip.start, clip.video.filename, self.pix_fmt, scale_clause, clip.get_duration(), filename )
            else:
                cmd = '%s -y -ss %f -i %s -pix_fmt %s -r 30000/1001 -qp 18 -an %s -t %f %s' % ( FFMPEG, clip.start, clip.video.filename, self.pix_fmt, scale_clause, clip.get_duration(), filename )               
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status == 0 and os.path.exists( filename ):
                Window.cache_dict[clip_hash] = filename
                Window.save_cache_dict()
            else:
                raise Exception( "Error producing clip file by %s at: %s" % ( cmd, filename ) )

        return filename

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

    def compute_duration( self, clips, include_overlay_timing=False ):
        '''Don't actually do anything, just report how long the clips will
        take to render in this window.
        
        Returns either a float (if include_overlay_timing is false), or
        a tuple with the float and an array of overlay timing data.

        The array of timing data has N elements, one for each clip of
        type Overlay, and each element is a start time, end time
        tuple.
        '''

        duration = 0
        pts_offset = 0
        overlay_timing = []
        overlay_prior_pts_offset = 0
        first_overlay = True
        for clip in clips:
            display = self.get_display( clip )

            # Compute the PTS offset for this clip.
            if display.display_style != OVERLAY:
                pts_offset += clip.get_duration()
                if pts_offset > duration:
                    duration = pts_offset

                # Set the value for the next iteration.
                overlay_prior_pts_offset = pts_offset
            else:
                # It's complicated if this is a cascading clip.

                # Initially we spin up to display.overlay_concurrency
                # clips going, one immediately and the rest followed
                # at display.overlay_min_gap intervals, we do this
                # until there could be more than
                # display.overlay_concurrency videos going at once.
                if len( overlay_timing ) < display.overlay_concurrency:
                    pts_offset = overlay_prior_pts_offset

                    if overlay_prior_pts_offset > 0:
                        pts_offset += display.overlay_min_gap
                    
                    overlay_timing.append( ( pts_offset, pts_offset + clip.get_duration() ) )

                    # Set the value for the next iteration.
                    overlay_prior_pts_offset = pts_offset

                else:
                    # Find the earliest time one of the most recently
                    # started overlay_concurrency clips are ending,
                    # this is our candidate for when to start the next
                    # clip.
                    pts_offset = min( sorted( [ x[1] for x in overlay_timing ] )[-display.overlay_concurrency:] )

                    if pts_offset - overlay_prior_pts_offset < display.overlay_min_gap:
                        # If not enough time has elapsed since we
                        # started a clip, push it out a bit.
                        pts_offset = overlay_prior_pts_offset + display.overlay_min_gap

                    overlay_timing.append( ( pts_offset, pts_offset + clip.get_duration() ) )

                    # Set the value for the next iteration.
                    overlay_prior_pts_offset = pts_offset

                if max( [ x[1] for x in overlay_timing ] ) > duration:
                    duration = max( [ x[1] for x in overlay_timing ] )
                    
        if include_overlay_timing:
            return ( duration, overlay_timing )
        else:
            return duration

    def get_child_windows( self, include_self=False ):
        '''Recursively get the list of all child windows.'''

        def flatten( l ):
            '''Internal only helper function for collapsing all nested window
            objects onto a single list.'''

            for el in l:
                if isinstance(el, collections.Iterable) and not isinstance(el, basestring):
                    for sub in flatten(el):
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

    * windows - A list of vsum.Window objects to distribut the clips
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
    will be added to the result, and some input clips mayu be unusued
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
        * windor_duration < min_duration

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

    # Internal only function to do the recusrive work of parseling out
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

    * output_file - If specified, the resulting file will be placed at output_file.  Default is to place it in the vsum module's temporary files location, which is by default 

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
    # Set some diplay properties.
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

    # Automatically distribute clips amongst windows..
    distribute_clips( [ c1, c2, c3, c8, cx, c4, c5, c6, c7 ], [ w1, w2, w3, w4 ], w0.duration )
    w0.output_file = 'output2.mp4'
    w0.render()
    '''
    pass
    
        
