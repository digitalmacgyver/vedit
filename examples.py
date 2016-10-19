#!/usr/bin/env python

import vedit

import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel( logging.DEBUG )

def example01():
    '''Clip 2 seconds out of the middle of a video.'''
    
    log.info( "Clipping 2 seconds out of source video from 1.5 seconds to 3.5 seconds." )
    source = vedit.Video( "./examples/testpattern.mp4" )
    clip = vedit.Clip( video=source, start=1.5, end=3.5 )
    window = vedit.Window( width=source.get_width(), 
                           height=source.get_height(),
                           output_file="./examples/example01.mp4" )
    window.clips = [ clip ]
    window.render()

    # Output at ./examples/example01.mp4

    return

if __name__ == "__main__":
    example01()
