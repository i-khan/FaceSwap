import dlib
import cv2
import numpy as np
import sys

import models
import NonLinearLeastSquares
import ImageProcessing

from drawing import *

import FaceRendering
import utils

import os
import subprocess

print "Press T to draw the keypoints and the 3D model"
print "Press R to start recording to a video file"

#you need to download shape_predictor_68_face_landmarks.dat from the link below and unpack it where the solution file is
#http://sourceforge.net/projects/dclib/files/dlib/v18.10/shape_predictor_68_face_landmarks.dat.bz2

#loading the keypoint detection model, the image and the 3D model
predictor_path = "../shape_predictor_68_face_landmarks.dat"
face_cvv_detector_path ="../mmod_human_face_detector.dat"
image_name = "../bnl/images/"+sys.argv[1]
#the smaller this value gets the faster the detection will work
#if it is too small, the user's face might not be detected
maxImageSizeForDetection = 960

#detector = dlib.cnn_face_detection_model_v1(face_cvv_detector_path) 
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(predictor_path)
mean3DShape, blendshapes, mesh, idxs3D, idxs2D = utils.load3DFaceModel("../candide.npz")

projectionModel = models.OrthographicProjectionBlendshapes(blendshapes.shape[0])

modelParams = None
lockedTranslation = False
drawOverlay = False
cap = cv2.VideoCapture("../data/"+sys.argv[2]+".mp4")

fourcc = cv2.VideoWriter_fourcc(*'XVID')

# Check if camera opened successfully
if (cap.isOpened()== False): 
  print("Error opening video stream or file")

cameraImg = cap.read()[1]

writer = None
if writer is None:
	print "Starting video writer"
	writer = cv2.VideoWriter("../bnl/videos/"+sys.argv[1]+"-out.avi", fourcc, 25,(cameraImg.shape[1], cameraImg.shape[0]))
	if writer.isOpened():
		print "Writer succesfully opened"
	else:
                writer = None
                print "Writer opening failed"



textureImg = cv2.imread(image_name)
textureCoords = utils.getFaceTextureCoords(textureImg, mean3DShape, blendshapes, idxs2D, idxs3D, detector, predictor)
renderer = FaceRendering.FaceRenderer(cameraImg, textureImg, textureCoords, mesh)

while True:
    cameraImg = cap.read()[1]
    try:
        shapes2D = utils.getFaceKeypoints(cameraImg, detector, predictor, maxImageSizeForDetection)

        if shapes2D is not None:
            for shape2D in shapes2D:
                #3D model parameter initialization
                modelParams = projectionModel.getInitialParameters(mean3DShape[:, idxs3D], shape2D[:, idxs2D])

                #3D model parameter optimization
                modelParams = NonLinearLeastSquares.GaussNewton(modelParams, projectionModel.residual, projectionModel.jacobian, ([mean3DShape[:, idxs3D], blendshapes[:, :, idxs3D]], shape2D[:, idxs2D]), verbose=0)

                #rendering the model to an image
                shape3D = utils.getShape3D(mean3DShape, blendshapes, modelParams)
                renderedImg = renderer.render(shape3D)

                #blending of the rendered face with the image
                mask = np.copy(renderedImg[:, :, 0])
                renderedImg = ImageProcessing.colorTransfer(cameraImg, renderedImg, mask)
                cameraImg = ImageProcessing.blendImages(renderedImg, cameraImg, mask,0.1)
        

                #drawing of the mesh and keypoints
                if drawOverlay:
                    drawPoints(cameraImg, shape2D.T)
                    drawProjectedShape(cameraImg, [mean3DShape, blendshapes], projectionModel, mesh, modelParams, lockedTranslation)

        if writer is not None:
            writer.write(cameraImg)

        cv2.imshow('image', cameraImg)
        key = cv2.waitKey(1)

        if key == 27:
            break
        if key == ord('t'):
            drawOverlay = not drawOverlay
    except:
        print("An exception occurred") 
        break

print "Stopping video writer"
writer.release()
writer = None

os.chdir('C://Users/Asus/')
# ffmpeg -i 1569831566308.jpeg-out.avi -i ../../data/superVideo2.mp4  -map 0:0 -map 1:1 -shortest 1569831566308.jpeg-out.mp4

subprocess.call(["ffmpeg", "-i", "../bnl/videos/"+sys.argv[1]+"-out.avi", "-i ", "../data/"+sys.argv[2]+".mp4", "-map ", "0:0", "-map ", "1:1", "-shortest", "../bnl/videos/"+sys.argv[1]+"-out.mp4" ])
