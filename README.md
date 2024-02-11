# earthcache
This is a repository for interacting with the Earthcache API offered by Skywatch to obtain satellite imagery. 
Start at the SDS_earthcache_api.py file to go through the functions offered. The API docs can be found at: https://api-docs.earthcache.com/

Currently, I've implemented functions to perform the following: 
- directly creating a pipeline 
- running a search
- creating a pipeline from a ran search
- downloading the images from a pipeline
- checking the status of a pipeline
- viewing the first image from the downloaded images 
- calculating the price of a pipeline

You'll need an API key from Earthcache, coordinates for the area from which you'd like images, the dates,
and what type of images you want. There are additional parameters that can be set, which can again be found at the API docs linked above.

This is useful for those looking to automate their workflow a little better in terms of obtaining satellite imagery! The alternative would be manually creating the pipeline through the dashboard each time you needed images. 

Reach out to tatooine888@gmail.com if you have any questions!
