#include <ecto/ecto.hpp>

#include <opencv2/highgui/highgui.hpp>

#include <boost/format.hpp>
#include <boost/filesystem.hpp>

#include <iostream>
#include <string>

//local highgui include
#include "highgui.h"

using ecto::tendrils;
namespace pt = boost::posix_time;
namespace fs = boost::filesystem;
namespace ecto_opencv
{

  struct VideoWriter
  {
    static void
    declare_params(tendrils& params)
    {
      params.declare<std::string>("video_file", "A video file name.", "video.mpg");
      params.declare<double>("fps", "Framerate of the created video stream.", 30);

      params.declare<Record::RecordCommands>("command", "The video recorder command", Record::START);
    }

    static void
    declare_io(const tendrils& params, tendrils& inputs, tendrils& outputs)
    {
      //set outputs
      inputs.declare<cv::Mat>("image", "Frame to record.").required(true);
    }

    void
    configure(const tendrils& params, const tendrils& inputs, const tendrils& outputs)
    {
      video_file = params.get<std::string>("video_file");
      fps = params.get<double>("fps");
      command = params["command"];
      frame = inputs["image"];
    }
    void
    start()
    {
      if (!writer)
      {
        writer.reset(new cv::VideoWriter);
      }
      if (!writer->isOpened())
      {
        std::cout << "Opening : " << video_file << std::endl;
        framesize = frame->size();
        bool success = writer->open(video_file, CV_FOURCC_DEFAULT, fps, framesize);
        if (!success)
          throw std::runtime_error("Could not open video file for writing: " + video_file);
      }
    }

    void
    stop()
    {
      writer.reset();
      std::cout << "Closed : " << video_file << std::endl;
    }

    void
    record()
    {
      start();
      if (frame->size() != framesize)
      {
        std::string msg = boost::str(
            boost::format("You may only record a constant size video frame. %dx%d != %dx%d") % framesize.width
            % framesize.height
            % frame->size().width
            % frame->size().height);
        throw std::runtime_error(msg);
      }
      cv::Mat temp;
      frame->copyTo(temp);
      writer->write(temp);
    }
    int
    process(const tendrils& inputs, const tendrils& outputs)
    {
      switch (*command)
      {
        case Record::START:
        case Record::RESUME:
          record();
          break;
        case Record::PAUSE:
          break;
        case Record::STOP:
          stop();
          break;
      }
      return ecto::OK;
    }
    boost::shared_ptr<cv::VideoWriter> writer;
    std::string video_file;
    cv::Size framesize;
    double fps;
    ecto::spore<cv::Mat> frame;
    ecto::spore<Record::RecordCommands> command;
  };
}
ECTO_CELL(highgui, ecto_opencv::VideoWriter, "VideoWriter", "Writes images to motion jpeg file.");
