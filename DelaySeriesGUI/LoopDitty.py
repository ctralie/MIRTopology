#Based off of http://wiki.wxpython.org/GLCanvas
#Lots of help from http://wiki.wxpython.org/Getting%20Started
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from OpenGL.arrays import vbo
from OpenGL.GL import shaders
import wx
from wx import glcanvas

from Cameras3D import *
from sys import exit, argv
import random
import numpy as np
import scipy.io as sio
import scipy.spatial as spatial
from pylab import cm
import os
import subprocess
import math
import time
from DelaySeries import *
import pygame.mixer
import time
import matplotlib.pyplot as plt

DEFAULT_SIZE = wx.Size(1200, 800)
DEFAULT_POS = wx.Point(10, 10)
MAXPOINTS = -1

def saveImageGL(mvcanvas, filename):
	view = glGetIntegerv(GL_VIEWPORT)
	img = wx.EmptyImage(view[2], view[3] )
	pixels = glReadPixels(0, 0, view[2], view[3], GL_RGB,
		             GL_UNSIGNED_BYTE)
	img.SetData( pixels )
	img = img.Mirror(False)
	img.SaveFile(filename, wx.BITMAP_TYPE_PNG)



def doPCA(DelaySeries, ncomponents = 3):
	DelaySeries = DelaySeries - np.min(DelaySeries, 0)
	DelaySeries = DelaySeries/np.max(DelaySeries, 0)
	X = DelaySeries - np.tile(np.mean(DelaySeries, 0), (DelaySeries.shape[0], 1))
	X[np.isinf(X)] = 0
	X[np.isnan(X)] = 0
	D = (X.T).dot(X)
	(lam, eigvecs) = linalg.eig(D)
	lam = np.abs(lam)
	varExplained = np.sum(lam[0:ncomponents])/np.sum(lam)
	print "2D Var Explained: %g"%(np.sum(lam[0:2])/np.sum(lam))
	eigvecs = eigvecs[:, 0:ncomponents]
	Y = X.dot(eigvecs)
	return (Y, varExplained)

#http://zetcode.com/wxpython/dialogs/
class DelaySeriesParamsDialog(wx.Dialog):
	def __init__(self, *args, **kw):
		super(DelaySeriesParamsDialog, self).__init__(*args, **kw)
		#Remember parameters from last time
		self.hopSizeDef = args[0].hopSize
		self.skipSizeDef = args[0].skipSize
		self.windowSizeDef = args[0].windowSize
		self.Fs = args[0].Fs
		self.filename = args[0].filename
		self.InitUI()
		self.SetSize((250, 200))
		self.SetTitle("Delay Series Parameters")


	def InitUI(self):
		pnl = wx.Panel(self)
		vbox = wx.BoxSizer(wx.VERTICAL)

		sb = wx.StaticBox(pnl, label='Parameters')
		sbs = wx.StaticBoxSizer(sb, orient=wx.VERTICAL)
		
		sbs.Add(wx.StaticText(pnl, label = self.filename))
		sbs.Add(wx.StaticText(pnl, label = "Sample Rate: %i"%self.Fs))

		hbox1 = wx.BoxSizer(wx.HORIZONTAL)        
		hbox1.Add(wx.StaticText(pnl, label='Hop Size'))
		self.hopSize = wx.TextCtrl(pnl)
		self.hopSize.SetValue("%i"%self.hopSizeDef)
		hbox1.Add(self.hopSize, flag=wx.LEFT, border=5)
		sbs.Add(hbox1)

		hbox2 = wx.BoxSizer(wx.HORIZONTAL)        
		hbox2.Add(wx.StaticText(pnl, label='Skip Size'))
		self.skipSize = wx.TextCtrl(pnl)
		self.skipSize.SetValue("%i"%self.skipSizeDef)
		hbox2.Add(self.skipSize, flag=wx.LEFT, border=5)
		sbs.Add(hbox2)
		
		hbox3 = wx.BoxSizer(wx.HORIZONTAL)        
		hbox3.Add(wx.StaticText(pnl, label='Window Size'))
		self.windowSize = wx.TextCtrl(pnl)
		self.windowSize.SetValue("%i"%self.windowSizeDef)
		hbox3.Add(self.windowSize, flag=wx.LEFT, border=5)
		sbs.Add(hbox3)

		pnl.SetSizer(sbs)

		hboxexit = wx.BoxSizer(wx.HORIZONTAL)
		okButton = wx.Button(self, label='Ok')
		closeButton = wx.Button(self, label='Close')
		hboxexit.Add(okButton)
		hboxexit.Add(closeButton, flag=wx.LEFT, border=5)

		vbox.Add(pnl, proportion=1, 
		flag=wx.ALL|wx.EXPAND, border=5)
		vbox.Add(hboxexit, 
		flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)

		self.SetSizer(vbox)

		okButton.Bind(wx.EVT_BUTTON, self.OnClose)
		closeButton.Bind(wx.EVT_BUTTON, self.OnClose)


	def OnClose(self, e):
		self.hopSize = int(self.hopSize.GetValue())
		self.skipSize = int(self.skipSize.GetValue())
		self.windowSize = int(self.windowSize.GetValue())
		self.Destroy()


class DensityThresholdDialog(wx.Dialog):
	def __init__(self, *args, **kw):
		super(DensityThresholdDialog, self).__init__(*args, **kw)
		#Remember parameters from last time
		self.densityNeighborsDef = args[0].densityNeighbors
		self.densityNPointsDef = args[0].densityNPoints
		self.lowDensityDef = args[0].lowDensity
		self.InitUI()
		self.SetSize((250, 200))
		self.SetTitle("Density Thresholding Parameters")


	def InitUI(self):
		pnl = wx.Panel(self)
		vbox = wx.BoxSizer(wx.VERTICAL)

		sb = wx.StaticBox(pnl, label='Parameters')
		sbs = wx.StaticBoxSizer(sb, orient=wx.VERTICAL)

		hbox1 = wx.BoxSizer(wx.HORIZONTAL)        
		hbox1.Add(wx.StaticText(pnl, label='Density Threshold'))
		self.densityNeighbors = wx.TextCtrl(pnl)
		self.densityNeighbors.SetValue("%s"%self.densityNeighborsDef)
		hbox1.Add(self.densityNeighbors, flag=wx.LEFT, border=5)
		sbs.Add(hbox1)

		hbox2 = wx.BoxSizer(wx.HORIZONTAL)        
		hbox2.Add(wx.StaticText(pnl, label='Number of Points'))
		self.densityNPoints = wx.TextCtrl(pnl)
		self.densityNPoints.SetValue("%i"%self.densityNPointsDef)
		hbox2.Add(self.densityNPoints, flag=wx.LEFT, border=5)
		sbs.Add(hbox2)

		self.lowDensity = wx.CheckBox(self, label="Low Density")
		self.lowDensity.SetValue(self.lowDensityDef)
		vbox.Add(self.lowDensity)

		pnl.SetSizer(sbs)

		hboxexit = wx.BoxSizer(wx.HORIZONTAL)
		okButton = wx.Button(self, label='Ok')
		closeButton = wx.Button(self, label='Close')
		hboxexit.Add(okButton)
		hboxexit.Add(closeButton, flag=wx.LEFT, border=5)

		vbox.Add(pnl, proportion=1, 
		flag=wx.ALL|wx.EXPAND, border=5)
		vbox.Add(hboxexit, 
		flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)

		self.SetSizer(vbox)

		okButton.Bind(wx.EVT_BUTTON, self.OnClose)
		closeButton.Bind(wx.EVT_BUTTON, self.OnClose)


	def OnClose(self, e):
		self.densityNeighbors = float(self.densityNeighbors.GetValue())
		self.densityNPoints = int(self.densityNPoints.GetValue())
		self.lowDensity = self.lowDensity.GetValue()
		self.Destroy()

class LoopDittyCanvas(glcanvas.GLCanvas):
	def __init__(self, parent):
		attribs = (glcanvas.WX_GL_RGBA, glcanvas.WX_GL_DOUBLEBUFFER, glcanvas.WX_GL_DEPTH_SIZE, 24)
		glcanvas.GLCanvas.__init__(self, parent, -1, attribList = attribs)	
		self.context = glcanvas.GLContext(self)
		
		self.parent = parent
		#Camera state variables
		self.size = self.GetClientSize()
		self.camera = MousePolarCamera(self.size.width, self.size.height)
		
		
		#Main state variables
		self.MousePos = [0, 0]
		self.initiallyResized = False
		
		self.bbox = np.array([ [1, 1, 1], [-1, -1, -1] ])
		random.seed()
		
		#Point cloud and playing information
		self.filename = ""
		self.X = np.array([])
		self.displayCount = 0
		self.SampleDelays = np.array([])
		self.Playing = False
		self.PlayIDX = 0
		self.DrawEdges = True
		
		self.GLinitialized = False
		#GL-related events
		wx.EVT_ERASE_BACKGROUND(self, self.processEraseBackgroundEvent)
		wx.EVT_SIZE(self, self.processSizeEvent)
		wx.EVT_PAINT(self, self.processPaintEvent)
		#Mouse Events
		wx.EVT_LEFT_DOWN(self, self.MouseDown)
		wx.EVT_LEFT_UP(self, self.MouseUp)
		wx.EVT_RIGHT_DOWN(self, self.MouseDown)
		wx.EVT_RIGHT_UP(self, self.MouseUp)
		wx.EVT_MIDDLE_DOWN(self, self.MouseDown)
		wx.EVT_MIDDLE_UP(self, self.MouseUp)
		wx.EVT_MOTION(self, self.MouseMotion)		
		#self.initGL()
	
	
	def processEraseBackgroundEvent(self, event): pass #avoid flashing on MSW.

	def processSizeEvent(self, event):
		self.size = self.GetClientSize()
		self.SetCurrent(self.context)
		glViewport(0, 0, self.size.width, self.size.height)
		if not self.initiallyResized:
			#The canvas gets resized once on initialization so the camera needs
			#to be updated accordingly at that point
			self.camera = MousePolarCamera(self.size.width, self.size.height)
			self.camera.centerOnBBox(self.bbox, math.pi/2, math.pi/2)
			self.initiallyResized = True

	def processPaintEvent(self, event):
		dc = wx.PaintDC(self)
		self.SetCurrent(self.context)
		if not self.GLinitialized:
			self.initGL()
			self.GLinitialized = True
		self.repaint()

	def startAnimation(self, evt):
		if len(self.SampleDelays) > 0:
			print "Playing %s"%self.filename
			self.Playing = True
			self.PlayIDX = 0
			s = pygame.mixer.Sound(self.filename)
			s.play()
			self.startTime = time.time()
			self.Refresh()

	def repaint(self):
		#Set up projection matrix
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		farDist = 3*np.sqrt(np.sum( (self.camera.eye - np.mean(self.bbox, 0))**2 ))
		nearDist = farDist/50.0
		gluPerspective(180.0*self.camera.yfov/np.pi, float(self.size.x)/self.size.y, nearDist, farDist)
		
		#Set up modelview matrix
		self.camera.gotoCameraFrame()	
		glClearColor(0.0, 0.0, 0.0, 0.0)
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		
		if len(self.X) > 0:
			glDisable(GL_LIGHTING)
			glColor3f(1, 0, 0)
			glPointSize(3)
			NPoints = self.X.shape[0]
			StartPoint = 0
			EndPoint = self.X.shape[0]-1
			if self.Playing:
				self.endTime = time.time()
				dT = self.endTime - self.startTime
				while dT > self.SampleDelays[self.PlayIDX]:
					self.PlayIDX = self.PlayIDX + 1
					if self.PlayIDX == NPoints - 1:
						self.Playing = False
				EndPoint = self.PlayIDX+1
				if MAXPOINTS != -1:
					StartPoint = max(EndPoint - MAXPOINTS, 0)
				self.Refresh()

			self.vbo.bind()
			glEnableClientState(GL_VERTEX_ARRAY)
			glVertexPointerf( self.vbo )
			
			self.XColorsVBO.bind()
			glEnableClientState(GL_COLOR_ARRAY)
			glColorPointer(3, GL_FLOAT, 0, self.XColorsVBO)
			
			if self.DrawEdges:
				glDrawArrays(GL_LINES, StartPoint, EndPoint - StartPoint + 1)
				glDrawArrays(GL_LINES, StartPoint+1, EndPoint)
			glDrawArrays(GL_POINTS, StartPoint, EndPoint - StartPoint + 1)
			self.XColorsVBO.unbind()
			self.vbo.unbind()
			glDisableClientState(GL_VERTEX_ARRAY)
			glDisableClientState(GL_COLOR_ARRAY)
		self.SwapBuffers()
		self.Refresh()
	
	def initGL(self):		
		glutInit('')
		glEnable(GL_NORMALIZE)
		glEnable(GL_DEPTH_TEST)

	def handleMouseStuff(self, x, y):
		#Invert y from what the window manager says
		y = self.size.height - y
		self.MousePos = [x, y]

	def MouseDown(self, evt):
		x, y = evt.GetPosition()
		self.CaptureMouse()
		self.handleMouseStuff(x, y)
		self.Refresh()
	
	def MouseUp(self, evt):
		x, y = evt.GetPosition()
		self.handleMouseStuff(x, y)
		self.ReleaseMouse()
		self.Refresh()

	def MouseMotion(self, evt):
		x, y = evt.GetPosition()
		[lastX, lastY] = self.MousePos
		self.handleMouseStuff(x, y)
		dX = self.MousePos[0] - lastX
		dY = self.MousePos[1] - lastY
		if evt.Dragging():
			if evt.MiddleIsDown():
				self.camera.translate(dX, dY)
			elif evt.RightIsDown():
				self.camera.zoom(-dY)#Want to zoom in as the mouse goes up
			elif evt.LeftIsDown():
				self.camera.orbitLeftRight(dX)
				self.camera.orbitUpDown(dY)
		self.Refresh()

class LoopDittyFrame(wx.Frame):
	(ID_LOADSONGFILE, ID_SAVESCREENSHOT, ID_ARCLENGTHDOWNSAMPLE, ID_DENSITYTHRESHOLD) = (1, 2, 3, 4)
	
	def setupPosColorVBO(self):
		idx = np.array([], dtype = 'int32')
		if self.TimbreCheckbox.GetValue():
			idx = np.append(idx, self.TimbreIdx)
		if self.MFCCCheckbox.GetValue():
			idx = np.append(idx, self.MFCCIdx)
		if self.ChromaCheckbox.GetValue():
			idx = np.append(idx, self.ChromaIdx)
		(self.glcanvas.X, self.varExplained) = doPCA(self.DelaySeries[:, idx])
		self.varExplainedTxt.SetValue("%g"%self.varExplained)
		self.glcanvas.vbo = vbo.VBO(np.array(self.glcanvas.X, dtype='float32'))
		cmConvert = cm.get_cmap('jet')
		self.glcanvas.XColors = cmConvert(np.linspace(0, 1, len(self.glcanvas.SampleDelays) ))[:, 0:3]
		self.glcanvas.XColorsVBO = vbo.VBO(np.array(self.glcanvas.XColors, dtype='float32'))		
	
	def ToggleFeature(self, evt):
		self.setupPosVBO()
		self.glcanvas.Refresh()
	
	def ToggleDisplayEdges(self, evt):
		self.glcanvas.DrawEdges = self.EdgesToggleCheckbox.GetValue()
		self.glcanvas.Refresh()
	
	def __init__(self, parent, id, title, pos=DEFAULT_POS, size=DEFAULT_SIZE, style=wx.DEFAULT_FRAME_STYLE, name = 'GLWindow'):
		style = style | wx.NO_FULL_REPAINT_ON_RESIZE
		super(LoopDittyFrame, self).__init__(parent, id, title, pos, size, style, name)
		#Initialize the menu
		self.CreateStatusBar()
		
		#Sound variables
		self.soundSamples = np.array([])
		pygame.mixer.init()
		self.hopSize = 512
		self.skipSize = 1
		self.windowSize = 43
		self.densityNeighbors = 3
		self.densityNPoints = 0
		self.lowDensity = False
		self.Fs = 22050
		self.varExplained = 0.0
		
		self.size = size
		self.pos = pos
		
		#Cached distance matrix
		self.D = np.array([])
		self.DistHist = (None, None)
		
		filemenu = wx.Menu()
		menuOpenSong = filemenu.Append(LoopDittyFrame.ID_LOADSONGFILE, "&Load Song File","Load Song File")
		self.Bind(wx.EVT_MENU, self.OnLoadSongFile, menuOpenSong)
		menuSaveScreenshot = filemenu.Append(LoopDittyFrame.ID_SAVESCREENSHOT, "&Save Screenshot", "Save a screenshot of the GL Canvas")
		self.Bind(wx.EVT_MENU, self.OnSaveScreenshot, menuSaveScreenshot)
		menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
		self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
		
		editmenu = wx.Menu()
		menuArcLengthDownsample = editmenu.Append(LoopDittyFrame.ID_ARCLENGTHDOWNSAMPLE, "&Downsample By Arc Length", "Downsample By Arc Length")
		self.Bind(wx.EVT_MENU, self.OnArcLengthDownsample, menuArcLengthDownsample)
		menuDensityThreshold = editmenu.Append(LoopDittyFrame.ID_DENSITYTHRESHOLD, "&Density Threshold Sample", "Density Threshold Sample")
		self.Bind(wx.EVT_MENU, self.OnDensitySubsample, menuDensityThreshold)
		
		# Creating the menubar.
		menuBar = wx.MenuBar()
		menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
		menuBar.Append(editmenu, "&Edit")
		self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
		self.glcanvas = LoopDittyCanvas(self)
		
		self.rightPanel = wx.BoxSizer(wx.VERTICAL)
		
		#Buttons to go to a default view
		animatePanel = wx.BoxSizer(wx.VERTICAL)
		self.rightPanel.Add(wx.StaticText(self, label="Animation Options"), 0, wx.EXPAND)
		self.rightPanel.Add(animatePanel, 0, wx.EXPAND)
		playButton = wx.Button(self, -1, "Play")
		self.Bind(wx.EVT_BUTTON, self.glcanvas.startAnimation, playButton)
		animatePanel.Add(playButton, 0, wx.EXPAND)
		#Checkbox for edge toggle
		self.EdgesToggleCheckbox = wx.CheckBox(self, label="Display Edges")
		self.EdgesToggleCheckbox.SetValue(True)
		self.EdgesToggleCheckbox.Bind(wx.EVT_CHECKBOX, self.ToggleDisplayEdges)
		animatePanel.Add(self.EdgesToggleCheckbox)
		#Checkboxes for CAF subsets
		self.TimbreCheckbox = wx.CheckBox(self, label="Timbre")
		self.TimbreCheckbox.SetValue(True)
		self.TimbreCheckbox.Bind(wx.EVT_CHECKBOX, self.ToggleFeature)
		animatePanel.Add(self.TimbreCheckbox)
		self.MFCCCheckbox = wx.CheckBox(self, label="MFCC")
		self.MFCCCheckbox.SetValue(True)
		self.MFCCCheckbox.Bind(wx.EVT_CHECKBOX, self.ToggleFeature)
		animatePanel.Add(self.MFCCCheckbox)
		self.ChromaCheckbox = wx.CheckBox(self, label="Chroma")
		self.ChromaCheckbox.SetValue(True)
		self.ChromaCheckbox.Bind(wx.EVT_CHECKBOX, self.ToggleFeature)
		animatePanel.Add(self.ChromaCheckbox)
		#Song Information
		animatePanel.Add(wx.StaticText(self, label = "Song Information"))
		hbox0 = wx.BoxSizer(wx.HORIZONTAL)
		hbox0.Add(wx.StaticText(self, label = 'Song Name'))
		self.songNameTxt = wx.TextCtrl(self)
		self.songNameTxt.SetValue("None")
		hbox0.Add(self.songNameTxt, flag = wx.LEFT, border = 5)
		animatePanel.Add(hbox0)
		
		hbox1 = wx.BoxSizer(wx.HORIZONTAL)        
		hbox1.Add(wx.StaticText(self, label='Hop Size'))
		self.hopSizeTxt = wx.TextCtrl(self)
		self.hopSizeTxt.SetValue("%i"%self.hopSize)
		hbox1.Add(self.hopSizeTxt, flag=wx.LEFT, border=5)
		animatePanel.Add(hbox1)

		hbox2 = wx.BoxSizer(wx.HORIZONTAL)        
		hbox2.Add(wx.StaticText(self, label='Skip Size'))
		self.skipSizeTxt = wx.TextCtrl(self)
		self.skipSizeTxt.SetValue("%i"%self.skipSize)
		hbox2.Add(self.skipSizeTxt, flag=wx.LEFT, border=5)
		animatePanel.Add(hbox2)
		
		hbox3 = wx.BoxSizer(wx.HORIZONTAL)        
		hbox3.Add(wx.StaticText(self, label='Window Size'))
		self.windowSizeTxt = wx.TextCtrl(self)
		self.windowSizeTxt.SetValue("%i"%self.windowSize)
		hbox3.Add(self.windowSizeTxt, flag=wx.LEFT, border=5)
		animatePanel.Add(hbox3)		
		
		hbox4 = wx.BoxSizer(wx.HORIZONTAL)        
		hbox4.Add(wx.StaticText(self, label='Sample Rate'))
		self.sampleRateTxt = wx.TextCtrl(self)
		self.sampleRateTxt.SetValue("%i"%self.Fs)
		hbox4.Add(self.sampleRateTxt, flag=wx.LEFT, border=5)
		animatePanel.Add(hbox4)

		hbox5 = wx.BoxSizer(wx.HORIZONTAL)        
		hbox5.Add(wx.StaticText(self, label='Variance Explained'))
		self.varExplainedTxt = wx.TextCtrl(self)
		self.varExplainedTxt.SetValue("%g"%self.varExplained)
		hbox5.Add(self.varExplainedTxt, flag=wx.LEFT, border=5)
		animatePanel.Add(hbox5)
		
		hbox6 = wx.BoxSizer(wx.HORIZONTAL)
		hbox6.Add(wx.StaticText(self, label='NumberPoints'))
		self.NumberPointsTxt = wx.TextCtrl(self)
		self.NumberPointsTxt.SetValue("0")
		hbox6.Add(self.NumberPointsTxt, flag=wx.LEFT, border=5)
		animatePanel.Add(hbox6)						
		
		#Finally add the two main panels to the sizer		
		self.sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.sizer.Add(self.glcanvas, 2, wx.EXPAND)
		self.sizer.Add(self.rightPanel, 0, wx.EXPAND)
		
		self.SetSizer(self.sizer)
		self.Layout()
		self.Show()
	
	def OnLoadSongFile(self, evt):
		dlg = wx.FileDialog(self, "Choose a file", ".", "", "*", wx.OPEN)
		if dlg.ShowModal() == wx.ID_OK:
			filename = dlg.GetFilename()
			dirname = dlg.GetDirectory()
			print "Loading %s...."%filename
			filepath = os.path.join(dirname, filename)
			name, ext = os.path.splitext(filepath)
			#TODO: Replace this ugly subprocess call with some Python
			#library that understand other files
			if ext.upper() != ".WAV":
				command = "avconv -i \"%s\" temp.wav"%filepath
				print command
				if "temp.wav" in set(os.listdir('.')):
					os.remove("temp.wav")
				subprocess.call(["avconv", "-i", filepath, "temp.wav"])
				filepath = "temp.wav"
			s = DelaySeries()
			Fs, X = wavfile.read(filepath)
			self.Fs = Fs
			self.filename = filename
			paramsDlg = DelaySeriesParamsDialog(self)
			paramsDlg.ShowModal()
			paramsDlg.Destroy()
			[self.hopSize, self.skipSize, self.windowSize] = [paramsDlg.hopSize, paramsDlg.skipSize, paramsDlg.windowSize]
			#Keep track of the original delay series and sample delays to allow
			#for arbitrary resampling later
			self.soundSamples, self.OrigDelaySeries, self.Fs, self.OrigSampleDelays, self.TimbreIdx, self.MFCCIdx, self.ChromaIdx = s.processFile(filepath, self.hopSize, self.skipSize, self.windowSize)
			self.DelaySeries = self.OrigDelaySeries.copy()
			self.glcanvas.SampleDelays = self.OrigSampleDelays.copy()
			self.NumberPointsTxt.SetValue("%i"%len(self.glcanvas.SampleDelays))
			self.setupPosColorVBO()
			self.glcanvas.filename = filepath
			self.glcanvas.camera.centerOnPoints(self.glcanvas.X)
			print "Loaded %s"%filename
			#Update GUI Elements
			self.songNameTxt.SetValue(filename)
			self.hopSizeTxt.SetValue("%i (%g s)"%(self.hopSize, self.hopSize/float(self.Fs)))
			self.skipSizeTxt.SetValue("%i (%g s)"%(self.skipSize, self.skipSize*self.hopSize/float(self.Fs) ))
			self.windowSizeTxt.SetValue("%i (%g s)"%(self.windowSize, self.windowSize*self.hopSize/float(self.Fs) ))
			self.sampleRateTxt.SetValue("%i"%self.Fs)
			self.glcanvas.Refresh()
		dlg.Destroy()
		return

	def OnSaveScreenshot(self, evt):
		dlg = wx.FileDialog(self, "Choose a file", ".", "", "*", wx.SAVE)
		if dlg.ShowModal() == wx.ID_OK:
			filename = dlg.GetFilename()
			dirname = dlg.GetDirectory()
			filepath = os.path.join(dirname, filename)
			saveImageGL(self.glcanvas, filepath)
		dlg.Destroy()
		return

	def OnArcLengthDownsample(self, evt):
		if len(self.soundSamples) == 0:
			return
		dlg = wx.TextEntryDialog(None,'Number of Points','Number of Points', '1')
		if dlg.ShowModal() == wx.ID_OK:
			#Need to resample and update DelaySeries and SampleDelays
			N = int(dlg.GetValue())
			OrigX = self.OrigDelaySeries
			OrigDelays = self.OrigSampleDelays
			#First compute the total arc length across the whole song
			sedges = [np.sqrt(np.sum( (OrigX[i, :] - OrigX[i-1])**2 )) for i in range(1, OrigX.shape[0])]
			sorig = np.cumsum(sedges)
			#Now resample uniformly along the curve
			snew = np.linspace(0, sorig[-1], N)
			SampleDelays = np.zeros(N)
			#First point is fixed
			SampleDelays[-1] = OrigDelays[-1]
			DelaySeries = np.zeros((N, OrigX.shape[1]))
			DelaySeries[0, :] = OrigX[0, :]
			#Fill in the rest of the points
			k = 0
			plt.subplot(1, 2, 1)
			plt.plot(sorig)
			plt.hold(True)
			plt.plot(snew)
			plt.xlabel('Sample Number')
			plt.ylabel('Arc Length')
			plt.legend(('Original', 'New'))
			plt.title('Arc Length')
			for i in range(1, N):
				while sorig[k] < snew[i]:
					k = k+1
				s0 = sorig[k-1]
				s1 = sorig[k]
				t = (snew[i] - s0)/(s1 - s0)
				#Linear interpolation
				DelaySeries[i, :] = (1-t)*OrigX[k-1, :] + t*OrigX[k, :]
				SampleDelays[i] = (1-t)*OrigDelays[k-1] + t*OrigDelays[k]
			plt.subplot(1, 2, 2)
			plt.plot(OrigDelays)
			plt.hold(True)
			plt.plot(SampleDelays)
			plt.xlabel('Sample Number')
			plt.ylabel('Sample Delay')
			plt.legend(('Original', 'New'))
			plt.title('Sample Delays')
			plt.show()
			self.DelaySeries = DelaySeries
			self.glcanvas.SampleDelays = SampleDelays
			self.setupPosColorVBO()
			self.NumberPointsTxt.SetValue("%i"%len(self.glcanvas.SampleDelays))
		dlg.Destroy()

	def OnDensitySubsample(self, evt):
		if len(self.soundSamples) == 0:
			return
		densityDlg = DensityThresholdDialog(self)
		densityDlg.ShowModal()
		densityDlg.Destroy()
		self.densityNeighbors = densityDlg.densityNeighbors
		self.densityNPoints = densityDlg.densityNPoints
		self.lowDensity = densityDlg.lowDensity
		
		#Find the first "densityNPoints" points in ascending order of max neighborhood point
		mask = np.zeros(self.OrigDelaySeries.shape[0])
		if len(self.D) == 0:
			self.D = spatial.distance_matrix(self.OrigDelaySeries, self.OrigDelaySeries)
		D = np.sort(self.D, 0)
		D = D[self.densityNeighbors, :]
		idx = np.argsort(D.flatten())
		if self.lowDensity:
			idx = idx[-self.densityNPoints:]
		else:
			idx = idx[0:self.densityNPoints]
		idx = np.sort(idx)
		self.DelaySeries = self.OrigDelaySeries[idx, :]
		self.glcanvas.SampleDelays = self.OrigSampleDelays[idx]
		self.setupPosColorVBO()
		self.NumberPointsTxt.SetValue("%i"%len(self.glcanvas.SampleDelays))
		
		
	def OnExit(self, evt):
		self.Close(True)
		return

class LoopDitty(object):
	def __init__(self):
		app = wx.App()
		frame = LoopDittyFrame(None, -1, 'LoopDitty')
		frame.Show(True)
		app.MainLoop()
		app.Destroy()

if __name__ == '__main__':
	app = LoopDitty()
