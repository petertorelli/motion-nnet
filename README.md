# Introduction

To help cut down on false positives when using [motion](https://motion-project.github.io/),
I created a server that sorts the movie events depending if their constituent images contain
a class from the MS COCO training set. It does this by a post-hook to `on_movie_end`.

I have my cameras running on an embedded Intel Core i5 fanless platform so
adding a GPU is not possible. Instead I plugged in a [Google USB Coral Accelerator TPU](https://coral.ai/products/accelerator)
stick and it is sufficient. Since the server queues the inferences after the pictures and
movie have both been written, it can take however long is necessary.

# Installation

You'll need to setup the PyCoral TPU libraries on your host machine. Once
that has been verified, you can test the server.

Add these line to your `motion.conf`, changing the location of this repo as
needed:

```
picture_filename %v-%Y%m%d%H%M%S-%q
movie_filename %v-%Y%m%d%H%M%S
on_movie_end /media/usbdisk/motion/nnet-sorter/client.py %f
```

# Operation

There are two threads: the socket listener & queue, and the inference
thread. This allows handling incoming requests in a performant way.

The server opens a socket and listens. The client sends it an MP4 full-
pathname. The file must start with `%v`, the event number, followed by
a hyphen. The server then scans all of the JPG files that start with the
prefix up to the hyphen. If it finds an object with 70% confidence, it
moves the mp4 file to a new directory.

Since images are recorded faster than they can be processed, we don't
want to block motion, so the client does not wait for a response.

# Example

In this example, first the server is started and put in the background, then
the client first sends a captured MP4 file, and then tells the server to exit.

TODO: Add an example that actually detects something. :)

## Example: server
```
$ ./server.py
Model loaded
Listening on port 19011
^Z
[1]+  Stopped                 ./server.py
$ bg
[1]+ ./server.py &
Queue: b'/media/usbdisk/motion/captures/13-20210812193848.mp4'
Checking 91 images in /media/usbdisk/motion/captures/13-20210812193848.mp4
check_image_file(/media/usbdisk/motion/captures/13-20210812193854-00.jpg) [1/91]...no objects
check_image_file(/media/usbdisk/motion/captures/13-20210812193854-06.jpg) [2/91]...no objects
check_image_file(/media/usbdisk/motion/captures/13-20210812193851-01.jpg) [3/91]...no objects
check_image_file(/media/usbdisk/motion/captures/13-20210812193850-01.jpg) [4/91]...no objects
:
:
check_image_file(/media/usbdisk/motion/captures/13-20210812193854-10.jpg) [90/91]...no objects
check_image_file(/media/usbdisk/motion/captures/13-20210812193850-07.jpg) [91/91]...no objects
...nothing to save
Queue: b'exit'
Exiting QueueThread on exception

[1]+  Done                    ./server.py
```

## Example: client
```
$ ./client.py /media/usbdisk/motion/captures/13-20210812193848.mp4
$ ./client.py exit
```

