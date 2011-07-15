#!/usr/bin/env python
PKG = 'ecto_projector'
import roslib; #roslib.load_manifest(PKG)
import ecto
from ecto_opencv import highgui, calib, imgproc, projector
import ecto_ros, ecto_sensor_msgs
from ecto_opencv import highgui
from optparse import OptionParser
import sys
from ecto_opencv_py.fiducial_pose_est import PoseFromFiducial

ImageSub = ecto_sensor_msgs.Subscriber_Image
CameraInfoSub = ecto_sensor_msgs.Subscriber_CameraInfo

DEBUG = True

########################################################################################################################

def parse_options():
    parser = OptionParser()
    parser.add_option("-c", "--config_file", dest="config_file",
                      help="the file containing the configuration")
    parser.add_option("-a", "--bag", dest="bag", help="The bag to analyze")

    (options, args) = parser.parse_args()
    return options

########################################################################################################################

def do_projector():
    options = parse_options()

    # define the input
    subs = dict(image=ImageSub(topic_name='camera/rgb/image_color', queue_size=0),
                depth=ImageSub(topic_name='camera/depth/image', queue_size=0),
                depth_info=CameraInfoSub(topic_name='camera/depth/camera_info', queue_size=0),
                image_info=CameraInfoSub(topic_name='camera/rgb/camera_info', queue_size=0),
             )

    sync = ecto_ros.Synchronizer('Synchronizator', subs=subs)

    im2mat_rgb = ecto_ros.Image2Mat()
    im2mat_depth = ecto_ros.Image2Mat()
    invert = imgproc.BitwiseNot()
    brg2rgb = imgproc.cvtColor('bgr -> rgb', flag=4)
    bgr2gray = imgproc.cvtColor('bgr -> gray', flag=7)

    camera_info = calib.CameraIntrinsics('Camera Info', camera_file="camera.yml")

    calibrator = projector.Calibrator()
    plasm = ecto.Plasm()
    offset_x = 0

    pose_from_fiducial = PoseFromFiducial(plasm,
                                        rows=5, cols=3,
                                        pattern_type="acircles",
                                        square_size=0.04,
                                        offset_x=offset_x,
                                        debug=DEBUG)
    pose_from_plane = projector.PlaneFitter()

    s1 = ecto.Strand()
    main_display = highgui.imshow("rgb show", name="rgb", waitKey=5, strand=s1)
    graph = [
                sync["image"] >> im2mat_rgb["image"],
                im2mat_rgb["image"] >> main_display[:],
                sync["depth"] >> im2mat_depth["image"],
                im2mat_depth["image"] >> (highgui.imshow("depth show", name="depth", waitKey= -1, strand=s1)[:],pose_from_plane['depth']),
                im2mat_rgb["image"] >> (brg2rgb["input"], bgr2gray["input"]),
                brg2rgb["out"] >> pose_from_fiducial['color_image'],
                bgr2gray["out"] >> pose_from_fiducial['image'],
                camera_info['K'] >> (pose_from_fiducial['K'],pose_from_plane['K']),
                pose_from_fiducial['debug_image'] >> highgui.imshow("pattern show", name="pattern", waitKey= -1, strand=s1)[:],
#                sync["image","depth"] >> pattern_detection['image', 'depth'],
#                pattern_detection['points'] >> projection_estimator['points']
            ]

    print "Press 's' to capture a view."
    pose_draw = calib.PoseDrawer('Plane Pose Draw')
    # add the display of the pattern
    video_display = highgui.imshow('pattern',
                               name='video_cap', waitKey=2, maximize=False, autoSize=True)
    warper = projector.FiducialWarper(projection_file='projector_calibration.yml')
    graph += [pose_from_fiducial['R', 'T', 'found'] >> (warper['R', 'T', 'found'],),
              pose_from_plane['R','T'] >> pose_draw['R', 'T'],
              camera_info['K'] >> pose_draw['K'],
              pose_from_fiducial['debug_image'] >> pose_draw['image'],
              pose_draw['output'] >> highgui.imshow("warped image", name="warped", waitKey= -1, strand=s1)[:],
              ]

    plasm.connect(graph)

    # display DEBUG data if needed
    if DEBUG:
        print plasm.viz()
        ecto.view_plasm(plasm)

    # execute the pipeline
    sched = ecto.schedulers.Singlethreaded(plasm)
    sched.execute()


if __name__ == "__main__":
    ecto_ros.init(sys.argv, "ecto_node")
    do_projector()
