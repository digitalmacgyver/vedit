#!/usr/bin/env python

import glob
import os
import random

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
              
def example05():
    '''Ovarlay videos on top of other videos.'''

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

def example06():
    '''Cascade overlayed videos and images in top of a base video or image.'''

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


    


example_files = [
    'a1.mp4',
    'a2.mp4',
    'a3.mp4',
    'cat02.jpg',
    'cat03.jpg',
    'cat04.jpg',
    'cat05.jpg',
    'cat06.jpg',
    'cat07.jpg',
    'dog01.jpg',
    'dog02.jpg',
    'dog03.jpg',
    'dog04.jpg',
    'dog05.jpg',
    'dog07.jpg',
    'dog08.jpg',
    'testpattern.mp4',
]

if __name__ == "__main__":
    # Check if the example files are installed where we expect them.
    example_dir = "./examples/"
    for example_file in example_files:
        if not os.path.exists( example_dir + example_file ):
            raise Exception( "Error - could not find example file: %s - perhaps you do not have them installed?  They are available in the GitHub repository for this project at: https://github.com/digitalmacgyver/vedit" % ( example_dir + example_file ) )

    try:
        os.mkdir( "./example_output" )
    except Exception as e:
        pass

    #example01()
    #example02()
    #example03()
    #example04()
    #example05()
    example06()
