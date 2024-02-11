"""
CREDIT ACKNOWLEDGEMENT: some of the code in this file comes from a public
github repository which can be found at: https://github.com/chris010970/earthcache    

"""

"""
This class directly interacts with the API to perform a variety of actions. 
SDS_earthcache_api.py uses these functions to complete the tasks outlined in this file. 
"""

import os
import wget
import uuid
import json
import time
import shutil
import pycurl
import certifi
import tempfile
import pandas as pd

from io import BytesIO
from io import StringIO
from datetime import datetime

class EcClient:

    def __init__(self, cfg_path, key, max_cost=0 ):

        """
        constructor
        """

        # read api key into string
        self._api_key = key
        print(key)
        
        # dictionary of api uris
        self._uris = {  'archive' : 'https://api.skywatch.co/earthcache/archive',
                        'base' : 'https://api.skywatch.co/earthcache' ,
                        'pipeline_price': 'https://api.skywatch.co/earthcache/pipelines/calculate'}

        # load template json objects from file            
        self._templates = dict()
        for key in [ 'search', 'pipeline', 'pipeline-search' ]:
            with open( os.path.join( cfg_path, f'{key}.json' ), ) as f:
                self._templates[ key ] = json.load( f )

        # copy args
        self._max_cost = max_cost

        return


# main functions!

    # runs a search based on the given area of interest 
    # https://api-docs.earthcache.com/#tag/post
    def processSearch( self, aoi, window, **kwargs ):

        """
        process search
        """

        # get delay
        delay = kwargs.get( 'delay', 2 )
        result = None

        # post search job
        search_id, status, _ = self.postSearch( aoi, window, **kwargs )
        if status == 200 and search_id is not None:

            # loop until error or search complete
            while True:

                # get search result
                status, result = self.getSearch( search_id )
                if status != 202:
                    break

                # delay between get requests
                time.sleep( delay )
        
        return status, result, search_id    
    

    # allows you to create a pipeline directly from a previously run search
    # https://api-docs.earthcache.com/#tag/pipelines/operation/PipelineCreate
    def createPipelineFromSearch( self, search_id, search_results, **kwargs ):

        """
        create pipeline
        """

        def getPayload():

            """
            get payload
            """

            # configure payload
            payload = self._templates[ 'pipeline-search' ]

            # get time range
            payload[ 'search_id' ] = search_id
            payload[ 'search_results' ] = search_results

            # assign max cost
            payload[ 'max_cost' ] = self._max_cost

            # for each template field
            for key in list( payload.keys() ):

                # replace tenplate values with kwargs
                value = kwargs.get( key )
                if value is not None:
                    payload[ key ] = value

            return payload

        # create request
        request = self.initRequest( self._uris[ 'base' ] + '/pipelines' )

        # get payload
        payload = json.dumps( getPayload() )

        # prepare post
        request.setopt( pycurl.POST, 1)
        request.setopt( pycurl.READDATA, StringIO( payload ) )
        request.setopt( pycurl.POSTFIELDSIZE, len( payload ) )

        # capture response
        response = BytesIO()
        request.setopt( pycurl.WRITEFUNCTION, response.write )

        # execute request
        request.perform()

        # return status code and response
        return request.getinfo(pycurl.RESPONSE_CODE ), json.loads( response.getvalue() )

    # creates the pipeline with the given parameters
    def createPipeline( self, name, start_date, end_date, aoi, **kwargs ):
        
        def getPayloadForPipeline():

            """
            get payload
            """

            # configure payload
            payload = self._templates[ 'pipeline' ]

            # assign max cost
            payload[ 'max_cost' ] = self._max_cost
            payload['name'] = name
            payload['start_date'] = start_date
            payload['end_date'] = end_date
            payload['aoi'] = aoi

            # for each template field
            for key in list( payload.keys() ):

                # replace tenplate values with kwargs
                value = kwargs.get( key )
                if value is not None:
                    payload[ key ] = value

            return payload

        # create request
        request = self.initRequest( self._uris[ 'base' ] + '/pipelines' )

        # get payload
        payload = json.dumps( getPayloadForPipeline() )

        # prepare post
        request.setopt( pycurl.POST, 1)
        request.setopt( pycurl.READDATA, StringIO( payload ) )
        request.setopt( pycurl.POSTFIELDSIZE, len( payload ) )

        # capture response
        response = BytesIO()
        request.setopt( pycurl.WRITEFUNCTION, response.write )

        # execute request
        request.perform()

        # return status code and response
        return request.getinfo(pycurl.RESPONSE_CODE ), json.loads( response.getvalue() )

    # still needs to be tested! 
    # Calculate cost of area and intervals of a pipeline, 
    # and the probability of collection of any tasking intervals
    # https://api-docs.earthcache.com/#tag/pipelinePost 
    def calculatePrice(self, resolution, location, start_date, end_date):
        """
        post search
        """
        

        parameters =  {'resolution': resolution,
                    'location': location,
                    'start_date': start_date, 
                    'end_date': end_date
                    }


        # get request
        request = self.initRequest( self._uris['pipeline_price'])

        # get payload
        payload = json.dumps(parameters)

        # prepare post
        request.setopt( pycurl.POST, 1)
        request.setopt( pycurl.READDATA, StringIO( payload ) )
        request.setopt( pycurl.POSTFIELDSIZE, len( payload ) )

        # capture response
        response = BytesIO()
        request.setopt( pycurl.WRITEFUNCTION, response.write )

        # execute request
        request.perform()

        # get status 
        status = request.getinfo(pycurl.RESPONSE_CODE ) 

        # return status code and response 
        return status, json.loads(response.getvalue())
    

# helper functions!

    def getSearch( self, search_id ):

        """
        get search
        """

        # execute get request
        return self.sendRequest( self._uris[ 'archive' ] + f'/search/{search_id}/search_results' )

    def getPipelines( self ):

        """
        get pipelines
        """

        # run get request
        return self.sendRequest( self._uris[ 'base' ] + '/pipelines' )

    def getPipeline( self, pipeline_id ):

        """
        get pipeline associated with id
        """

        # run get request
        return self.sendRequest( self._uris[ 'base' ] + f'/pipelines/{pipeline_id}' )

    def getPipelineIdFromName( self, name ):

        """
        get pipeline associated with id
        """

        pipeline_id = None

        # run get request
        status, result = self.sendRequest( self._uris[ 'base' ] + f'/pipelines' )
        if status == 200:

            # parse into dataframe
            df = pd.DataFrame( result[ 'data'] )
            df = df[ df['name'] == name ]

            # get id from row
            if len( df == 1 ):
                pipeline_id = df[ 'id' ].iloc[ 0 ]
        
        return pipeline_id

    def deletePipeline( self, pipeline_id ):

        """
        delete pipeline
        """

        # run custom delete request
        return self.sendRequest( self._uris[ 'base' ] + f'/pipelines/{pipeline_id}', action='DELETE' )



        return request.getinfo(pycurl.RESPONSE_CODE ), json.loads( response.getvalue() )
    
    def postSearch( self, aoi, window, **kwargs ):

            """
            post search
            """

            def getPayload():

                """
                get payload
                """

                # configure payload
                payload =  self._templates[ 'search' ]
                payload[ 'location' ] = aoi

                # get time range
                payload[ 'start_date' ] = window[ 'start_date' ]
                payload[ 'end_date' ] = window[ 'end_date' ]

                # for each template field
                for key in payload.keys():

                    # replace tenplate values with kwargs
                    value = kwargs.get( key )
                    if value is not None:
                        payload[ key ] = value

                return payload

            # get request
            search_id = None
            request = self.initRequest( self._uris[ 'archive' ] + '/search' )

            # get payload
            payload = json.dumps( getPayload() )

            # prepare post
            request.setopt( pycurl.POST, 1)
            request.setopt( pycurl.READDATA, StringIO( payload ) )
            request.setopt( pycurl.POSTFIELDSIZE, len( payload ) )

            # capture response
            response = BytesIO()
            request.setopt( pycurl.WRITEFUNCTION, response.write )

            # execute request
            request.perform()

            # get status 
            status = request.getinfo(pycurl.RESPONSE_CODE ) 
            if status == 200:

                # parse response for search id
                obj = json.loads( response.getvalue() )
                if 'data' in obj:
                    search_id = obj[ 'data' ][ 'id' ]

            # return status code and response 
            return search_id, status, json.loads( response.getvalue() )

    def getIntervalResults( self, pipeline_id ):

        """
        get interval results
        """

        # run get request
        return self.sendRequest( self._uris[ 'base' ] + f'/pipelines/{pipeline_id}/interval_results' )

    def getImages( self, results, out_path ):

        """
        get request
        """

        def getDateTimePath( metafile ):

            """
            get datetime path
            """

            with open( metafile ) as f:
                data = json.load( f )
                dt = datetime.strptime( data[ 'ProductInfo' ][ 'PRODUCT_SCENE_RASTER_START_TIME' ], '%d-%b-%Y %H:%M:%S.%f')
                
            return dt.strftime( '%Y%m%d_%H%M%S' )


        images = []

        # convert to dataframe if required
        if not isinstance( results, pd.DataFrame ):
            results = pd.DataFrame( results )

        for row in results.itertuples():

            # download metadata file
            with tempfile.TemporaryDirectory() as tmpdir:
                print ( '... downloading {url}'.format( url=row.metadata_url ) )
                metafile = wget.download( row.metadata_url, out=tmpdir )

                # determine datetime path from matadata
                path = os.path.join( out_path, getDateTimePath( metafile ) )
                if not os.path.exists( path ):
                    os.makedirs( path )

                # move metadata file to out_path if not exists
                pathname = os.path.join( path, os.path.basename( row.metadata_url ) )
                if not os.path.exists( pathname ):
                    shutil.move( metafile, path )

            # download scientific dataset to out_path datetime folder
            pathname = os.path.join( path, os.path.basename( row.analytics_url ) )
            if not os.path.exists( pathname ):
                print ( '... downloading {url}'.format( url=row.analytics_url ) )
                images.append( wget.download( row.analytics_url, out=path ) )

        return images

    def getOutputs( self ):

        """
        get request
        """

        # run get request
        return self.sendRequest( self._uris[ 'base' ] + f'/outputs' )

    def getOutputIdFromName( self, name ):

        """
        get request
        """

        output_id = None

        # run get request
        status, result = self.sendRequest( self._uris[ 'base' ] + f'/outputs' )
        if status == 200:

            # parse into dataframe
            df = pd.DataFrame( result[ 'data'] )
            df = df[ df['name'] == name ]

            # get id from row
            if len( df == 1 ):
                output_id = df[ 'id' ].iloc[ 0 ]
        
        return output_id     

    def getOutput( self, output_id ):

        """
        get request
        """

        # run get request
        return self.sendRequest( self._uris[ 'base' ] + f'/outputs/{output_id}' )

    def initRequest( self, uri ):

        """
        get request
        """

        # setup curl object - add ssl certification
        request = pycurl.Curl()
        request.setopt( pycurl.CAINFO, certifi.where() )

        # add uri + header
        request.setopt( pycurl.URL, uri )
        request.setopt( pycurl.HTTPHEADER, self.getHeaderParams() ) 

        return request

    def sendRequest( self, uri, action='GET', status_ok=[ 200 ] ):

        """
        get request
        """

        # create request
        request = self.initRequest( uri )

        # configure request type
        if action == 'GET':
            request.setopt( pycurl.HTTPGET, 1)
        else:
            request.setopt( pycurl.CUSTOMREQUEST, action )

        # capture response to request
        response = BytesIO()
        request.setopt( pycurl.WRITEFUNCTION, response.write )

        # execute request
        request.perform()

        # return status and response
        return request.getinfo(pycurl.RESPONSE_CODE), json.loads( response.getvalue() )

    def getHeaderParams( self ):

        """
        get header parameters + values
        """

        # return header attributes
        return [    'Accept: application/json',
                    'Content-Type: application/json',
                    'x-api-key: {key}'.format( key=self._api_key ) ]

    