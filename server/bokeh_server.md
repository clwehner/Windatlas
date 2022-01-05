# Notes on creating a Bokeh server for a *Windatlas-App* 

In this document I am going to collect notes and thoughts on how to setup an improove a web-app for the windatlas and mastr use case.

## Running a Bokeh server

### Introduction

These notes are based on the *[Bokeh server tutorial page](https://docs.bokeh.org/en/2.4.1/docs/user_guide/server.html)*.

- converts python objects into JSON to pass them to its client library, BokehJS
- R and Scala are supported as well
- use periodic, timeout, and asynchronous callbacks to drive streaming updates
- **The primary purpose of the Bokeh server is to synchronize data between the underlying Python environment and the BokehJS library running in the browser**
- can be run in a local network, as well as on the internet
- Bokeh server uses the application code to create individual sessions and documents for all connecting browsers

### Simple local applications

#### *Single module*

Basic example of an app which adds random numbers to a location:

```python
# myapp.py

from random import random

from bokeh.layouts import column
from bokeh.models import Button
from bokeh.palettes import RdYlBu3
from bokeh.plotting import figure, curdoc

# create a plot and style its properties
p = figure(x_range=(0, 100), y_range=(0, 100), toolbar_location=None)
p.border_fill_color = 'black'
p.background_fill_color = 'black'
p.outline_line_color = None
p.grid.grid_line_color = None

# add a text renderer to the plot (no data yet)
r = p.text(x=[], y=[], text=[], text_color=[], text_font_size="26px",
           text_baseline="middle", text_align="center")

i = 0

ds = r.data_source

# create a callback that adds a number in a random location
def callback():
    global i

    # BEST PRACTICE --- update .data in one step with a new dict
    new_data = dict()
    new_data['x'] = ds.data['x'] + [random()*70 + 15]
    new_data['y'] = ds.data['y'] + [random()*70 + 15]
    new_data['text_color'] = ds.data['text_color'] + [RdYlBu3[i%3]]
    new_data['text'] = ds.data['text'] + [str(i)]
    ds.data = new_data

    i = i + 1

# add a button widget and configure with the call back
button = Button(label="Press Me")
button.on_click(callback)

# put the button and plot in a layout and add to the document
curdoc().add_root(column(button, p))
```

In order to run the .py file as an app locally enter the following command in the terminal:

```
bokeh serve --show myapp.py
```

The `--show` option will cause your default browser to open a new tab at the address of the running application, which in this case is:

```
http://localhost:5006/myapp
```

#### *Directory format*

You can run the app from a named directory as well. This way you can add more utility scrips to advance the usage. For the following command, the app has to be located in a directory called `myapp`:

```
bokeh serve --show myapp
```

This directory must contain a `main.py` file that constructs a document for the Bokeh server to serve:

```
myapp
   |
   +---main.py
```

The following is the directory app structure that the Bokeh server is familiar with:

```
myapp
   |
   +---__init__.py
   +---app_hooks.py
   +---main.py
   +---request_handler.py
   +---static
   +---theme.yaml
   +---templates
        +---index.html
```
