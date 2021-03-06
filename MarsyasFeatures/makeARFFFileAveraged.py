import subprocess
import os
import numpy as np
import scipy.io as sio
import pickle

if __name__ == '__main__':
	genreIndex = open('../MusicDownloader/Music/index.txt', 'r')
	genreNames = [s.rstrip() for s in genreIndex.readlines()]
	genreIndex.close()
	
	arffName = "songs_AllFeaturesAveraged.arff"
	arffAttributesFile = open('attributesAveraged.arff', 'r')
	attributes = [s.rstrip() for s in arffAttributesFile.readlines()]
	arffFile = open(arffName, 'w')
	arffFile.write("@relation %s\n"%arffName)
	for s in attributes:
		arffFile.write("%s\n"%s)
	arffFile.write("@attribute genre {")
	for i in range(0, len(genreNames)):
		arffFile.write("\"%s\""%genreNames[i])
		if i < len(genreNames) - 1:
			arffFile.write(",")
	arffFile.write("}\n")
	arffFile.write("@attribute artist string\n")
	arffFile.write("@attribute album string\n")
	arffFile.write("@attribute title string\n")
	arffFile.write("\n\n@data\n")
	attributes = [a.split("@attribute ")[1] for a in attributes]
	
	os.chdir('../MusicDownloader/Music')
	dirNum = 0
	songsFeatures = np.array([])
	songsInfo = []
	genreIndex = {}
	for genre in genreNames:
		print "Reading directory %i..."%dirNum
		songsIndex = open("%i/index.txt"%dirNum, 'r')
		songsLines = songsIndex.readlines()
		songsLines = [s.rstrip() for s in songsLines]
		#This now assumes additional data has been collected from discogs
		for i in range(0, len(songsLines)/6): 
			#filename, song.artist, song.album, song.title
			i1 = i*6
			filename = songsLines[i1]
			artist = songsLines[i1 + 1]
			album = songsLines[i1 + 2]
			title = songsLines[i1 + 3]
			year = songsLines[i1 + 4]
			genres = songsLines[i1 + 5]
			genres = genres.split("[")[1]
			genres = genres.split("]")[0]
			genres = [g.lstrip().rstrip()[2:-1] for g in genres.split(",")]			
			for genre in genres:
				if not genre in genreIndex:
					genreIndex[genre] = len(genreIndex)
			genresInt = [genreIndex[genre]+1 for genre in genres]
			genresInt = np.array(genresInt)
			
			#Step 1: Extract .wav file
			wavName = "%s.wav"%(filename.split(".m4a")[0])
			filepath = "%i/%s"%(dirNum, filename)
			if not os.path.isfile(filepath):
				print "WARNING: %s not found"%filepath
				continue
			wavpath = "%i/%s"%(dirNum, wavName)
			command = "avconv -i %s -ac 1 %s"%(filepath, wavpath)
			print command
			subprocess.call(["avconv", "-i", filepath, "-ac", "1", wavpath])
			#Step 2: Create a collection file with this .wav file
			mfhandle = open('temp.mf', 'w')
			mfhandle.write(wavpath)
			mfhandle.close()
			#Step 3: call bextract to extract the features
			# https://github.com/marsyas/marsyas/blob/master/src/apps/bextract/bextract.cpp
			#bextract 0.mf -w out.arff --downsample 2 -fe -sv -mfcc -zcrs -ctd -rlf -flx -sfm -scf -chroma
			subprocess.call(["bextract", "temp.mf", "-w", "temp.arff", "--downsample", "2", "-fe", "-sv", "-mfcc", "-zcrs", "-ctd", "-rlf", "-flx", "-chroma", "-bf"])
			temparffhandle = open('temp.arff', 'r')
			lines = temparffhandle.readlines()[-1]
			fields = lines.split(",")
			fields = fields[0:-1]
			temparffhandle.close()
			#Step 4: Write the features to the ARFF file with all songs
			for field in fields:
				arffFile.write("%s,"%field)
			arffFile.write("\"%s\",\"%s\",\"%s\",\"%s\"\n"%(genre.replace("\"", ""), artist.replace("\"", ""), album.replace("\"", ""), title.replace("\"", "")))
			#Step 5: Concatenate data to the numpy arrays
			featuresArray = np.array([ [float(x) for x in fields] ])
			if np.prod(songsFeatures.shape) == 0:
				songsFeatures = featuresArray
			else:
				songsFeatures = np.concatenate([songsFeatures, featuresArray])
			songsInfo.append({'filepath':"%s"%filepath, 'artist':artist, 'album':album, 'title':title, 'year':int(year), 'genres':genresInt})
			#Step 6: Remove the .wav file to free up space
			if os.path.isfile(wavName):
				os.remove(wavName)
		dirNum = dirNum+1
		#Save the matrix at intermediate steps
		sio.savemat("songs_AllFeaturesAveraged.mat", {'songsFeatures':songsFeatures, 'songsInfo':songsInfo, 'featureNames':attributes})
		songsIndex.close()
	os.chdir('../../MarsyasFeatures')
	#Save a matlab version
	genreStrings = [0]*len(genreIndex)
	for genre in genreIndex:
		genreStrings[genreIndex[genre]] = genre
	sio.savemat("songs_AllFeaturesAveraged.mat", {'songsFeatures':songsFeatures, 'songsInfo':songsInfo, 'featureNames':attributes, 'genreStrings':genreStrings})
	#Also save a pickled version so it's convenient for me to go back and look in Python
	fout = open("songs_AllFeaturesAveraged.txt", 'w')
	pickle.dump( (songsFeatures, songsInfo, attributes, genreStrings), fout)
	fout.close()
