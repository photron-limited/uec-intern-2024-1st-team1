import unittest, sys, time
import numpy as np

import pypuclib
from pypuclib import CameraFactory, Camera, XferData, Resolution, Decoder, FramerateLimit
from pypuclib import PUCException, WrapperException
from pypuclib import PUC_COLOR_TYPE

import time

# need to connect camera and run test
class pypuclib_onlinetest(unittest.TestCase):

    def setUp(self):
        print(sys._getframe().f_code.co_name)
        self.isCallbacked = False
        self.cam = CameraFactory().create()

    def tearDown(self):
        print(sys._getframe().f_code.co_name)
        self.cam.close()
        return super().tearDown()

    def test_resolution(self):
        max_reso = self.cam.resolutionMax()
        limit_reso = self.cam.resolutionLimit()

        # over max resolution violation
        with self.assertRaises(PUCException):
            self.cam.setResolution(max_reso.width + 8, max_reso.height)
        with self.assertRaises(PUCException):
            self.cam.setResolution(max_reso.width, max_reso.height + 8)

        # less than min resolution violation
        with self.assertRaises(PUCException):
            self.cam.setResolution(limit_reso.limitW.min - 1, max_reso.height)
        with self.assertRaises(PUCException):
            self.cam.setResolution(max_reso.height, limit_reso.limitH.min - 1)

        # resolution step violation
        with self.assertRaises(PUCException):
            self.cam.setResolution(max_reso.width - limit_reso.limitW.step - 1,
                                   max_reso.height)
        with self.assertRaises(PUCException):
            self.cam.setResolution(max_reso.width,
                                   max_reso.height - limit_reso.limitH.step - 1)

        # set maximum resolution
        target = Resolution(max_reso.width, max_reso.height)
        self.cam.setResolution(target.width, target.height)
        res = self.cam.resolution()
        self.assertEqual(res, target)

        # set minimum resolution
        target = Resolution(limit_reso.limitW.min, limit_reso.limitH.min)
        self.cam.setResolution(target.width, target.height)
        res = self.cam.resolution()
        self.assertEqual(res, target)

        # set step of resolution(width)
        target = Resolution(max_reso.width - limit_reso.limitW.step, 
                            max_reso.height)
        self.cam.setResolution(target.width, target.height)
        res = self.cam.resolution()
        self.assertEqual(res, target)

        # set step of resolution(height)
        target = Resolution(max_reso.width, 
                            max_reso.height - limit_reso.limitH.step)
        self.cam.setResolution(target.width, target.height)
        res = self.cam.resolution()
        self.assertEqual(res, target)

    def test_framerate_shutter(self):
        # shutter speed smaller than framerate violation
        fps = self.cam.framerate()
        with self.assertRaises(PUCException):
            self.cam.setShutter(fps - 100)
        with self.assertRaises(PUCException):
            self.cam.setFramerateShutter(fps, fps - 100)

        # setMaxtimumFramerate
        print(self.cam.resolution())
        target = self.cam.framerateMax()
        self.cam.setFramerate(target)
        self.assertEqual(self.cam.framerate(), target)
        self.cam.setFramerateShutter(target, target)
        self.assertEqual(self.cam.framerateShutter(), tuple([target, target]))

        # setFramerate and shutter
        target = [2000, 4000]
        self.cam.setFramerate(target[0])
        self.assertEqual(self.cam.framerate(), target[0])
        self.cam.setShutter(target[1])
        self.assertEqual(self.cam.shutter(), target[1])
        target = [4000, 8000]
        self.cam.setFramerateShutter(target[0], target[1])
        self.assertEqual(self.cam.framerateShutter(), tuple(target))

    def test_colortype(self):
        # device color mono only for now
        self.assertEqual(self.cam.colortype(), PUC_COLOR_TYPE.PUC_COLOR_MONO)

    def test_ringubuffer_count(self):
        # set over range violation
        with self.assertRaises(PUCException):
            self.cam.setRingBufferCount(-5)
        with self.assertRaises(PUCException):
            self.cam.setRingBufferCount(3)
        with self.assertRaises(PUCException):
            self.cam.setRingBufferCount(66666)

        target = 64
        self.cam.setRingBufferCount(target)
        self.assertEqual(self.cam.ringBufferCount(), target)
    
    def test_xfer_timeout(self):
        target = [1000, 1000]
        self.cam.setXferTimeout(target[0], target[1])
        self.assertEqual(self.cam.xferTimeout(), tuple(target))
        target = [0, 0]
        self.cam.setXferTimeout(target[0], target[1])
        self.assertNotEqual(self.cam.xferTimeout(), tuple(target))

    def callback(self, xferData):
        self.isCallbacked = True

    def test_xfer(self):
        # haven't start yet
        self.assertFalse(self.cam.isXferring())

        self.cam.beginXfer(self.callback)
        self.assertTrue(self.cam.isXferring())
        time.sleep(1)
        self.assertTrue(self.isCallbacked)

        # xfer ended
        self.cam.endXfer()
        self.assertFalse(self.cam.isXferring())

    def test_grab(self):
        decoder = self.cam.decoder()
        xferdata = self.cam.grab()

        self.assertEqual(xferdata.resolution(), self.cam.resolution())

        # decode array and Xferdata should be same
        img1 = decoder.decode(xferdata)
        img2 = decoder.decode(xferdata.data(), 
                              xferdata.resolution())
        self.assertTrue(np.array_equal(img1, img2))

        # sequenceNo of extract from array and XferData as should be same 
        seq = decoder.extractSequenceNo(xferdata.data(),
                                        xferdata.resolution().width,
                                        xferdata.resolution().height)
        self.assertEqual(seq, xferdata.sequenceNo())

    def test_framerateLimit(self):
        limit = self.cam.framerateLimit()

        # over max framerate
        with self.assertRaises(PUCException):
            self.cam.setFramerate(limit.limitMax + 1)

        # less than min framerate
        with self.assertRaises(PUCException):
            self.cam.setFramerate(limit.limitMin - 1)

    def test_resetDevice(self):
        self.cam.beginXfer(self.callback)
        self.cam.endXfer()
        self.cam.resetDevice()
        self.cam.beginXfer(self.callback)

        self.assertTrue(self.cam.isXferring())
        time.sleep(1)
        self.assertTrue(self.isCallbacked)

    def test_resetSequenceNo(self):
        decoder = self.cam.decoder()

        while(1):
            xferData1 = self.cam.grab()

            seq = decoder.extractSequenceNo(xferData1.data(),
                                            xferData1.resolution().width,
                                            xferData1.resolution().height)
            if(seq < 1000) or (seq > 64535):
                time.sleep(2)
  
            else:
                break

        self.cam.resetSequenceNo()

        xferData2 = self.cam.grab()

        seq_reset = decoder.extractSequenceNo(xferData2.data(),
                                        xferData2.resolution().width,
                                        xferData2.resolution().height)

        self.assertTrue(seq_reset <= seq)

    def test_fanState(self):
        tmp = self.cam.fanState()
        # turn off the fan
        self.cam.setFanState(False)
        state = self.cam.fanState()
        self.assertEqual(state, False)

        # turn on the fan
        self.cam.setFanState(True)
        state = self.cam.fanState()
        self.assertEqual(state, True)

    def test_sensorTemperature(self):
        temperature = self.cam.sensorTemperature()
        print("sensor temperature=%d" %(temperature))
        self.assertTrue(0 <= temperature <= 100)
        




if __name__ == '__main__':
    unittest.main()