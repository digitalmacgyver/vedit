#!/usr/bin/env python

import os

import vedit

import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel( logging.DEBUG )

def example01():
    '''Clip 2 seconds out of the middle of a video.'''
    
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
    return

def example02():
    '''Resize an existing video a few different ways.'''

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
              
    return
    
def example03():
    '''Put two videos next to each other.'''

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

    return

def example04():
    '''Replace the audio track of a video.'''

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

    return
              
if __name__ == "__main__":
    # DEBUG - check the existence of the demo files!!!

    try:
        os.mkdir( "./example_output" )
    except Exception as e:
        pass

    #example01()
    #example02()
    #example03()
    example04()