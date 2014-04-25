#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append("web2py")
sys.path.append("bin/modules")

import argparse
import logging
import os
import shutil

from modules.db.Corpus_DB import Corpus_DB
from modules.db.CorpusStats_DB import CorpusStats_DB
from modules.db.LDA_DB import LDA_DB
from modules.db.LDAStats_DB import LDAStats_DB
from modules.db.ComputeCorpusStats import ComputeCorpusStats
from modules.db.ComputeLDAStats import ComputeLDAStats

from modules.apps.CreateApp import CreateApp
from modules.apps.SplitSentences import SplitSentences
from modules.readers.GensimReader import GensimReader

def ImportGensimLDA( app_name, model_path, corpus_path, database_path, is_quiet, force_overwrite ):
	logger = logging.getLogger( 'termite' )
	logger.addHandler( logging.StreamHandler() )
	logger.setLevel( logging.INFO if is_quiet else logging.DEBUG )
	
	app_path = 'apps/{}'.format( app_name )
	corpus_filename = '{}/corpus.txt'.format( corpus_path )
	database_filename = '{}/corpus.db'.format( database_path )
	logger.info( '--------------------------------------------------------------------------------' )
	logger.info( 'Import a gensim LDA topic model as a web2py application...' )
	logger.info( '           app_name = %s', app_name )
	logger.info( '           app_path = %s', app_path )
	logger.info( '         model_path = %s', model_path )
	logger.info( '    corpus_filename = %s', corpus_filename )
	logger.info( '  database_filename = %s', database_filename )
	logger.info( '--------------------------------------------------------------------------------' )
	
	if force_overwrite or not os.path.exists( app_path ):
		with CreateApp(app_name) as app:
			# Create a copy of the original corpus
			app_database_filename = '{}/corpus.db'.format( app.GetDataPath() )
			logger.info( 'Copying [%s] --> [%s]', database_filename, app_database_filename )
			shutil.copy( database_filename, app_database_filename )
			
			# Import corpus (models/corpus.db, data/corpus.txt, data/sentences.txt)
			app_corpus_filename = '{}/corpus.txt'.format( app.GetDataPath() )
			logger.info( 'Copying [%s] --> [%s]', corpus_filename, app_corpus_filename )
			shutil.copy( corpus_filename, app_corpus_filename )
			app_sentences_filename = '{}/sentences.txt'.format( app.GetDataPath() )
			logger.info( 'Extracting [%s] --> [%s]', corpus_filename, app_sentences_filename )
			SplitSentences( corpus_filename, app_sentences_filename )
			app_db_filename = '{}/corpus.db'.format( app.GetDatabasePath() )
			logger.info( 'Copying [%s] --> [%s]', database_filename, app_db_filename )
			shutil.copy( database_filename, app_db_filename )
			
			# Compute derived-statistics about the corpus
			db_path = app.GetDatabasePath()
			with Corpus_DB(db_path) as corpus_db:
				with CorpusStats_DB(db_path, isInit=True) as corpusStats_db:
					computer = ComputeCorpusStats( corpus_db, corpusStats_db, app_corpus_filename, app_sentences_filename )
					computer.Execute()
			
				# Mark 'corpus' as available
				corpus_db.AddModel('corpus', 'Text corpus')
				
				# Import model
				app_model_path = '{}/gensim-lda'.format( app.GetDataPath() )
				logger.info( 'Copying [%s] --> [%s]', model_path, app_model_path )
				shutil.copytree( model_path, app_model_path )
			
				# Compute derived-statistics about the model
				with LDA_DB(db_path, isInit=True) as lda_db:
					reader = GensimReader( app_model_path, lda_db )
					reader.Execute()
					with LDAStats_DB(db_path, isInit=True) as ldaStats_db:
						computer = ComputeLDAStats( lda_db, ldaStats_db )
						computer.Execute()
				
				# Mark 'lda' as available
				corpus_db.AddModel('lda', 'LDA model')
			
	else:
		logger.info( '    Already available: %s', app_path )

def main():
	parser = argparse.ArgumentParser( description = 'Import a gensim topic model as a web2py application.' )
	parser.add_argument( 'app_name'     , type = str , help = 'Web2py application identifier' )
	parser.add_argument( 'model_path'   , type = str , help = 'A folder containing gensim LDA topic model output' )
	parser.add_argument( 'corpus_path'  , type = str , help = 'A folder containing a text corpus as a tab-delimited file named "corpus.txt"' )
	parser.add_argument( 'database_path', type = str , help = 'A folder containing a text corpus and its metadata as a SQLite3 database named "corpus.db"' )
	parser.add_argument( '--quiet'      , const = True , default = False , help = 'Show fewer debugging messages', action = 'store_const' )
	parser.add_argument( '--overwrite'  , const = True , default = False , help = 'Overwrite any existing model', action = 'store_const' )
	args = parser.parse_args()
	ImportGensimLDA( args.app_name, args.model_path, args.corpus_path, args.database_path, args.quiet, args.overwrite )

if __name__ == '__main__':
	main()
