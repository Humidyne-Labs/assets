# Object Inversion Solution Draft

### The Issue:
currently when we render 14pt font then attempt to invert the font and binding box, the result is unreadable by a human. 

### Previous Attempted Solutions and Preliminary Investigation Scope
1.) both "style" and "direct" color change methods have produced the same unreable result on the display, conclusion, issue still exists.
2.) changing the luminosity threshold value to something greater than 127 has produced the same unreable result on the display. the working hypothesis was that the antialias of the font engine was impacting the bit depth reduction in a negative way. this hypothesis assumes the font is not stored as a static bitmapped asset, and that the engine renders the font per point size, and dpi, dynamicly, from a unified source asset consisting of soft edges or transparencies.
3.) comparisons between the application code and virtual LVGL instance reveals that the issue can not be reproduced. the hardware results, differ from the virtually generated screen image. this has made debugging the issue visually, invalid.
4.) inspection of the BSP and sdkconfig files have resulted in the following conclusion, the bsp is stable and working as intended, the configuration file is valid for the hardware. confirming there is no issue with the bsp or sdkconfig file.
5.) during extensive testing, at one point in time, the bsp rendered the entire screen buffer, inverted. the results were very human readable. these results did not match the results of the inversion test, the conclusion is, the display is capable of rendering inverted 14pt text that is human readable. the issue, by deduction, must be the way in which we are inverting the text during runtime.

# Proposed Solutions to the Outstanding Issue
1.) each object (I think) has an associated draw buffer/canvas. if we manually invert the bit in the object buffer, we can effectively invert the objects color, bypassing any font rendering issue. this assumes the objects buffer is sized proportionally to the object. a draw buffer equal to that of the screen size will render this method of inversion invalid for applications. this solution is based on assumption.
2.) we could manually invert a windowed area of the internal screen buffer. the function may look like the following definition. err_val invert_screen_buffer(x,y,h,w, bool); by completely bypassing the LVGL middleware, we can ensure a full but level inversion. however, doing so invalidates the LVGL screen update mechanism. this would result in a bit level inversion that remains unrendered on screen.
3.) we convert the 14pt font asset to a indexable bitmap, with a bit depth reduction of 1. we then use the conventional font engine, assuming it supports this font format. then use conventional means to invert the object per the LVGL recommended flow. this will hopefully bypass any rendering issue caused by the following, threshold value, antialias, transparency, scale transform, dpi to font point transform. this solution is based on assumption.
4.) we update to version 9.6.0-1 and hope that this update resolves the current issue. solution based on speculation, magic pixie dust, and dragon farts.
5.) please create a test plan for validation, please also include some original solutions to the aforementioned inversion issue. it is my hope that between me and you, we can come up with a viable solution to the issue, that is valid for an application.

### End of Object Inversion Draft



