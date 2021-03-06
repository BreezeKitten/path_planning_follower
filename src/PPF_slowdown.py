#!/usr/bin/env python

# LDSC published.

import numpy as np
import matplotlib.pyplot as plt
import math as m
import rospy
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Pose, PoseWithCovarianceStamped, Point, Quaternion, Twist
import tf

V_avg = 0.2  # control veloctiy by this term
V_min = 0.05 # slowdown minimum velocity
V_max = 0.25 # maximum velocity
W_max = 1
slowdown = 1 #slowdown factor

# Do NOT change all variables
S = 0.0
A = 0
deltaT = 0.01
L = 0.4
Xd = []
Yd = []
thetad = []
Vd = []
Wd = []
t = 0
Xnow = 0
Ynow = 0
yaw = 0
theta_final = m.pi*3/2
Vcom = 0
Wcom = 0
subgoal_x = 0
subgoal_y = 0
theta_f = 0

cmd_vel_topic = "cmd_vel"
com_pub = rospy.Publisher(cmd_vel_topic,Twist,queue_size=10)
path_pub = rospy.Publisher("desired_path",Path,queue_size=10)


# publish the Path update @ 20190504
def Path_publish(X,Y):
    com_path = Path()
    com_path.header.frame_id = "map"
    for i in range(0,len(X)-1):
	pose = PoseStamped()
	pose.pose.position.x = X[i]
	pose.pose.position.y = Y[i]
	com_path.poses.append(pose)
    path_pub.publish(com_path)
    

def path_cal(P1,P2,P3,goal):
    global theta_f
    S = 0
    X_d = []
    Y_d = []
    theta_d = []
    X_d_dot = []
    Y_d_dot = []
    V_d = []
    W_d = []
    
    X_i = P1[0]
    Y_i = P1[1]
    theta_i = P1[2]
   # theta_i = m.atan2((P2[1]-P1[1]),(P2[0]-P1[0]))

    X_f = P2[0]
    Y_f = P2[1]
    theta_f = m.atan2((P3[1]-P2[1]),(P3[0]-P2[0]))

    k = m.sqrt((X_i - X_f) ** 2 + (Y_i - Y_f) ** 2)
    ax = k * m.cos(theta_f) - 3 * X_f
    
    ay = k * m.sin(theta_f) - 3 * Y_f
    bx = k * m.cos(theta_i) + 3 * X_i
    by = k * m.sin(theta_i) + 3 * Y_i
    Xs = [X_f-X_i+ax+bx,3*X_i-ax-2*bx,-3*X_i+bx,X_i]
    Ys = [Y_f-Y_i+ay+by,3*Y_i-ay-2*by,-3*Y_i+by,Y_i]

    
    for j in range(0,1000):
        S = S + m.sqrt((np.polyval(Xs,j/1000)-np.polyval(Xs,(j+1)/1000))**2 +(np.polyval(Ys,j/1000)-np.polyval(Ys,(j+1)/1000))**2)

    k = S
    ax = k * m.cos(theta_f) - 3 * X_f
    ay = k * m.sin(theta_f) - 3 * Y_f
    bx = k * m.cos(theta_i) + 3 * X_i
    by = k * m.sin(theta_i) + 3 * Y_i
    Xs = [X_f-X_i+ax+bx,3*X_i-ax-2*bx,-3*X_i+bx,X_i]
    Ys = [Y_f-Y_i+ay+by,3*Y_i-ay-2*by,-3*Y_i+by,Y_i]

    if goal == 1:
	Vavg = max(min(V_avg*S/slowdown,V_avg),V_min)
	print(Vavg)
    else:
	Vavg = V_avg
    A = round(k/(Vavg*deltaT))
#    if goal == True:
#        for j in range(0,int(A)+2):
#            X_d.append(np.polyval(Xs,j/A))
#            Y_d.append(np.polyval(Ys,j/A))
#    else:
    for j in range(0,int(A)+2): #A+2 just test
            X_d.append(np.polyval(Xs,j/A))
            Y_d.append(np.polyval(Ys,j/A))


    for i in range(0,int(A)+1):
        X_d_dot.append((X_d[i+1] - X_d[i])/deltaT)
        Y_d_dot.append((Y_d[i+1] - Y_d[i])/deltaT)
        theta_d.append(m.atan2(Y_d_dot[i],X_d_dot[i]))
 #       if i > 0:
 #           if(theta_d[i] > theta_d[i-1] + m.pi):
  #              theta_d[i] = theta_d[i] - 2 * m.pi
        V_d.append(m.sqrt((X_d_dot[i])**2 + (Y_d_dot[i])**2))

    for i in range(0,int(A)):
        W_d.append((theta_d[i+1] - theta_d[i])/deltaT)

    return X_d,Y_d,theta_d,V_d,W_d


def Vel_command(X,Y,theta,X_d,Y_d,theta_d,V_d,W_d):
    a = 0.5
    damp = 0.7
    k1 = 2*damp*a
    k3 = k1
    k2 = (a ** 2 - W_d ** 2) / V_d
    
    e1 = (X_d - X) * m.cos(theta) + (Y_d - Y) * m.sin(theta)
    e2 = -(X_d - X) * m.sin(theta) + (Y_d - Y) * m.cos(theta)
    e3 = theta_d - theta
    u1 = -k1 * e1
    if(abs(e3) > m.pi):
	e3 = e3 + 2 * m.pi
    u2 = -k2 * e2 - k3 * e3
#    print(e3,theta_d)
    V_com = V_d * m.cos(e3) - u1
    W_com = W_d - u2
    

    return V_com,W_com

def command_pub(Vcom,Wcom):
    global t

    
    vel_msg = Twist()
    vel_msg.linear.x = Vcom # /V_max if you need 0~1 output
    vel_msg.linear.y = 0
    vel_msg.linear.z = 0
    vel_msg.angular.x = 0
    vel_msg.angular.y = 0    
    vel_msg.angular.z = Wcom # /W_max if you need 0~1 output
    
    com_pub.publish(vel_msg)
    t = t + 1
 
    return
# command below if using Twist /robot pose
def posecallback(data):
    global Xnow
    global Ynow
    global yaw 
    global Vcom
    global Wcom
    Xnow = data.pose.pose.position.x
    Ynow = data.pose.pose.position.y
    yaw = data.pose.pose.orientation.z
#    print(Xnow,Ynow,yaw)
    if t < len(Vd)-1:
        Vcom,Wcom = Vel_command(Xnow,Ynow,yaw,Xd[t],Yd[t],thetad[t],Vd[t],Wd[t])
    else:
        Vcom = 0
        Wcom = 0
    
    if(abs(Vcom) > V_max):
	Vcom = np.sign(Vcom) * V_max
    if(abs(Wcom) > W_max):
	Wcom = np.sign(Wcom) * W_max
#    print(Vcom,Wcom)
#    command_pub(Vcom,Wcom)

    return
####################

# command below if using Odometry /robot pose
"""	
def posecallback(data):
    global Xnow
    global Ynow
    global yaw 
    global Vcom
    global Wcom
    Xnow = data.linear.x
    Ynow = data.linear.y
#    odom_quat = (data.pose.pose.orientation.x,data.pose.pose.orientation.y,data.pose.pose.orientation.z,data.pose.pose.orientation.w)
#    euler = tf.transformations.euler_from_quaternion(odom_quat)
#    yaw = euler[2]
    yaw = data.angular.z
#    print(Xnow,Ynow,yaw)
    if t < len(Vd)-1:
        Vcom,Wcom = Vel_command(Xnow,Ynow,yaw,Xd[t],Yd[t],thetad[t],Vd[t],Wd[t])
    else:
        Vcom = 0
        Wcom = 0
    
    if(abs(Vcom) > V_max):
	Vcom = np.sign(Vcom) * V_max
    if(abs(Wcom) > W_max):
	Wcom = np.sign(Wcom) * W_max
#    print(Vcom,Wcom)
#    command_pub(Vcom,Wcom)

    return
"""
######################

def subgoalCB(data):
    global Xd
    global Yd
    global thetad
    global Vd
    global Wd
    global t
    global subgoal_x
    global subgoal_y
    subgoal_x = data.linear.x
    subgoal_y = data.linear.y
    direct_x = data.linear.z
    direct_y = data.angular.x
    goal = data.angular.y
    if (abs(Xnow-subgoal_x) > 0.08) or (abs(Ynow-subgoal_y) > 0.08) or (abs(yaw - theta_f) > 0.2):
    	Xd,Yd,thetad,Vd,Wd = path_cal([Xnow,Ynow,yaw],[subgoal_x,subgoal_y],[direct_x,direct_y],goal)
    Path_publish(Xd,Yd)
    t = 0
    return



if __name__ == '__main__':
    rospy.init_node('PPF',anonymous=True)
    rate = rospy.Rate(1/deltaT)
    sub = rospy.Subscriber("/robot_pose",Odometry,posecallback)
    #sub = rospy.Subscriber("/robot_pose",Twist,posecallback) ## For Twist pose input
    sub2 = rospy.Subscriber("/subgoal_position",Twist,subgoalCB)
    while not rospy.is_shutdown():
	if (abs(Xnow-subgoal_x) < 0.05) & (abs(Ynow-subgoal_y) < 0.05) & (abs(yaw - theta_f)< 0.3):
	    Vcom = 0
	    Wcom = 0
	command_pub(Vcom,Wcom)
	rate.sleep()	 
    


