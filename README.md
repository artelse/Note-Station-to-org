## Note: Note Station to org is forked from [Note station to markdown](https://github.com/Maboroshy/Note-Station-to-markdown) and heavily edited for my own needs.

Also note that the script like in the original doesn't handle linefeeds very well affecting formatting of text.

*Original readme follows*
  
This script will convert notes from Synology Note Station to plain-text markdown notes.  
The script is written in Python and should work on any desktop platform. It's tested on Linux, Windows 7, mac OS 10.15.

After conversion you will get:
1) Directories named like the exported notebooks;
2) Notes in those directories as markdown-syntax plain text files with all in-line images in-place;
3) Assigned tags and links to attachments at the beginning of note text;
4) All images and attached files in `media` sub-directories inside notebook directories.

## Local installation

1) The script requires [Python 3.5+](https://www.python.org/downloads/) and [pandoc](http://pandoc.org/installing.html) installed on your system. Get the install package or use the package manager of your OS.
2) Put `nsx2md.py` to the directory, where you want to convert notes.
3) (Linux only, optional) Give `nsx2md.py` "execute" permission.

# Usage
1) Export your Synology Note Station notebooks by: Setting -> Import and Export -> Export. You will get .nsx file.
2) Adjust the .nsx file permission if required. Mine was readable only by owner user.
3) Copy the .nsx file(s) to the directory where you've put `nsx2md.py`.
4) Set option settings if required - see the "Optional settings" section below.
5) Run `nsx2md.py` or `python nsx2md.py` to convert all the .nsx files in the directory. It won't delete them.  

... or run `nsx2md.py path/to/export.nsx` to convert a specific file. Converted notes will appear where the file is.

`nsx2md.py` can be located anywhere as long as you specify the file you want to convert.

## Docker setup

build Docker image  

`docker build -t nsx2md .`  

run the docker image  

`docker run -it -v "$PWD:/nsx2md nsx2md <file.nsx>`  


# Optional settings
Inside the script you can make some adjustments to the link format and notes metadata:  
Select meta data options:  
`meta_data_in_yaml` - `True`  YAML block the following meta data that are set True, `False` meta data will be in text;  
`insert_title` - `True` to insert note title as a markdown heading at the first line, `False` to disable;  
`insert_ctime` - `True` to insert note creation time to the beginning of the note text, `False` to disable;  
`insert_mtime` - `True` to insert note modification time to the beginning of the note text, `False` to disable;  
`tags` -  `True` to insert list of tags, `False` to disable;  
`tag_prepend` - string to prepend each tag in a tag list inside the note, default is empty;  
`tag_delimiter` - string to delimit tags, default is comma separated list;  
`no_spaces_in_tags` - `True` to replace spaces in tag names with '_', `False` to keep spaces.

Select file link options:  
`links_as_URI` - `True` for `file://link%20target` style links, `False` for `/link target` style links;  
`absolute_links` - `True` for absolute links, `False` for relative links;  

Select File/Attachments/Media options:  
`media_dir_name` - name of the directory inside the produced directory where all images and attachments will be stored;   
`md_file_ext` - extension for produced markdown syntax note files;  
`creation_date_in_filename` - `True` to insert note creation time to the note file name, `False` to disable;

# For [QOwnNotes](https://github.com/pbek/QOwnNotes) users
There are several ways to get tags from converted notes to work in QOwnNotes:

## Import tags to QOwnNotes native way
1) Convert .nsx files with default `nsx2md.py` settings;
2) Add notebook directories produced by `nsx2md.py` as QOwnNotes note folders;  
3) Set one of these note folders as current;  
4) Enable provided `import_tags.qml` script in QOwnNotes (Note -> Settings -> Scripting) (`remove_tag_line.py` should be at the same directory);  
5) The script will add 2 new buttons and menu items:  
    `1. Import tags` - to import tags from the tag lines of all the notes in the current note folder  
    `2. Remove tag lines` - to remove the tag lines from all the notes in the current folder  
6) Use the buttons in the according order, any previous QOwnNotes tag data for the note folder will be lost;  
7) Move to the next note folder produced by `nsx2md.py`, repeat #5;  
8) Disable `import_tags.qml` script. That is obligatory.

## "@tag tagging in note text (experimental)" QOwnNotes script
1) For default `@` tag prepends use the following `nsx2md.py` settings:
``` ini
tag_prepend = '@'  # string to prepend each tag in a tag list inside the note, default is empty
tag_delimiter = ' '  # string to delimit tags, default is comma separated list
no_spaces_in_tags = True  # True to replace spaces in tag names with '_', False to keep spaces
```
2) Convert .nsx files;
3) Add notebook directories produced by `nsx2md.py` as QOwnNotes note folders.
