# How to automaticaly run a python script daily on Linux using CRON-Jobs

## Checking the CRON-schedual manager on your Linux for existing CRON-Jobs

CRON is a software on Linux and Mac that allows you to automate scrips in a regularity of your choice.
To check your existing CRON-Jobs, type `crontab -l` in your terminal.


## Setting up a new CRON-Job

#### Understanding the repetition rate syntax

In order to set the repetion rate, we have to understand the sytax to set that rate. The Webpage [crontab.guru](https://crontab.guru/) helps you figuring out your desired rate.

I for now want to start the python script to update the MaStR-DB every morning from *Monday to Friday at 04:00 am*:

*0 4 * * 1-5*


#### Creating new CRON-Job

The following example expects the *vim* editor to be your default editor in your terminal. To check your default editor, enter `echo $EDITOR` in your terminal. If the output is empty or some thing else, you can switch your terminal editor by entering the following command into your terminal: `export EDITOR=vim` .

To edit CRON-Jobs enter `crontab -e` into yout terminal. If your default editor is vim, press `i` to enter **-INSERT MODE-**. Now you can add a new Job to the probably still empty list. For example running a test logging script every minute:

###### test.py file:

```python
import logging
import os

dir_path = os.path.dirname(os.path.realpath(__file__))
filename = os.path.join(dir_path, 'test_log.log')

print(filename)

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(filename)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

def do_logging():
    logger.info("test")


if __name__ == '__main__':
    do_logging()
```

###### Line to enter in crontab:

The path to your python file can differ and depends on where you have created it.

`* * * * * python ~/Documents/code/Windatlas/windatlas/mastr/autoUpdate/test.py`

After inserting, press `esc` to exit **-INSERT MODE-** and type `:wq` to save and exit the vim editor.

#### Create a virtual environment using conda to run your CRON-Job in

I wanted to show this option in order to have a slim virtual environment that is only used for certain CRON-Jobs. This will prevent failure in the running CRON-Jobs by new packeges or updates to used packages, which might influence the running code. 

Too create a new conda environment, enter `conda create -n cronUpdate python=3.8.12 requests bs4 urllib3 pandas numpy sqlalchemy` into your terminal.
Or if you want to create an evironment by an `.yml` file: `conda env create -f environmentCron.yml`