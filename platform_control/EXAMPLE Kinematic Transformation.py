import numpy as np
import time
import matplotlib.pyplot as plt
from collections import deque
from datetime import datetime, timedelta
import serial  # For serial communication

# Initialize system parameters
rBall = 0.1  # meters, ball radius
rOmni = 0.025  # meters, omniwheel radius
beta = 120  # degrees between omniwheels
rZ = 0.05  # meters, height above equator
rX = 0.08  # meters, distance from center

# PID controller gains
kP = 1.0
kI = 0.1
kD = 0.05

# Data storage and timing parameters
BUFFER_DURATION = 60.0  # seconds to store in buffer
SAMPLE_TIME = 0.001  # seconds (control loop period)
DATA_FIELDS = ['timestamp', 'setpoint_omni', 'feedback_omni', 'omni_error', 
               'setpoint_ball', 'feedback_ball', 'ball_error']

# Test parameters
TEST_LAG_MULTIPLIER = 5  # Number of sample times to lag behind
ERROR_PERCENTAGE = 0.01  # 1% maximum error
TEST_FREQUENCY = 0.1  # Hz, frequency of sinusoidal test signal

class DataBuffer:
    def __init__(self, buffer_duration, sample_time):
        self.max_points = int(buffer_duration / sample_time)
        self.data = {field: deque(maxlen=self.max_points) for field in DATA_FIELDS}
        self.buffer_duration = buffer_duration

    def add_data(self, **kwargs):
        for field, value in kwargs.items():
            if field in self.data:
                self.data[field].append(value)

    def get_time_vector(self):
        """Returns time vector relative to newest sample"""
        if len(self.data['timestamp']) == 0:
            return np.array([])
        newest_time = self.data['timestamp'][-1]
        return np.array([t - newest_time for t in self.data['timestamp']])

class TestSignalGenerator:
    def __init__(self, sample_time, lag_multiplier, error_percentage):
        self.sample_time = sample_time
        self.lag_samples = lag_multiplier
        self.error_percentage = error_percentage
        self.setpoint_history = deque(maxlen=lag_multiplier + 1)
        self.time = 0
        
    def generate_setpoint(self):
        """Generate a test setpoint signal"""
        # Generate three sinusoidal components with different phases
        wx = np.sin(2 * np.pi * TEST_FREQUENCY * self.time)
        wy = np.sin(2 * np.pi * TEST_FREQUENCY * self.time + 2*np.pi/3)
        wz = np.sin(2 * np.pi * TEST_FREQUENCY * self.time + 4*np.pi/3)
        
        setpoint = np.array([wx, wy, wz])
        self.setpoint_history.append(setpoint)
        self.time += self.sample_time
        return setpoint
    
    def generate_feedback(self):
        """Generate feedback with lag and small error"""
        if len(self.setpoint_history) <= self.lag_samples:
            return np.zeros(3)
        
        # Get historical setpoint (implementing lag)
        lagged_setpoint = self.setpoint_history[0]
        
        # Add small random error (within error_percentage)
        error = np.random.uniform(-self.error_percentage, self.error_percentage, 3)
        feedback = lagged_setpoint * (1 + error)
        
        return feedback

def jacobian(ballRot, beta, rBall, rOmni, rZ, rX):
    """
    Calculates the Jacobian and inverse Jacobian matrices for a ball driven by 3 omniwheels
    """
    # Define angles for each omniwheel
    beta1 = np.radians(0)
    beta2 = np.radians(beta)
    beta3 = np.radians(2 * beta)
    
    # Initialize Jacobian matrix
    jacob = np.zeros((3,3))

    jacob[0,0] = rZ;    jacob[0,1] = rZ * np.cos(beta2);    jacob[0,2] = rZ * np.cos(beta3)
    jacob[1,0] = 0;     jacob[1,1] = -rZ * np.sin(beta2);   jacob[1,2] = -rZ * np.sin(beta3)
    jacob[2,0] = -rX;   jacob[2,1] = -rX;                   jacob[2,2] = -rX

    jacob = (rOmni/rBall**2) * jacob
    
    # Calculate inverse of Jacobian matrix
    jacobInv = np.linalg.inv(jacob)
    
    return jacobInv, jacob

def omniAngVel(setpointBallAngVel, jacobInv):
    """
    Calculates the angular velocities of the three omniwheels
    """
    setpointBallAngVel = np.array(setpointBallAngVel)
    omniAngVel = np.dot(jacobInv, setpointBallAngVel)
    return omniAngVel

def calculateBallAngVelFeedback(encoderOmniAngVel, jacob):
    """
    Calculates actual ball rotation from encoder feedback
    """
    feedbackBallAngVel = np.dot(jacob, encoderOmniAngVel)
    return feedbackBallAngVel

def generateSetpointBallAngVel():
    """
    Placeholder function to generate desired ball rotation vector
    """
    setpointBallAngVel = np.array([0.0, 0.0, 1.0])  # rad/s [wx, wy, wz]
    return setpointBallAngVel

def getOmniEncoder():
    """
    Placeholder function to get encoder feedback over serial
    """
    encoderOmniAngVel = np.array([0.0, 0.0, 0.0])
    return encoderOmniAngVel

def sendSetpointAngVel(setpointOmniAngVel):
    """
    Placeholder function to send angular velocity setpoints over serial
    """
    # TODO: Implement actual serial communication
    pass

def initializePlots():
    """
    Initialize the plotting environment with four subplots
    """
    plt.ion()  # Enable interactive plotting
    fig = plt.figure(figsize=(12, 10))
    
    # Create 2x2 grid of subplots
    ax1 = plt.subplot(221)  # Omniwheel velocities
    ax2 = plt.subplot(222)  # Ball rotation
    ax3 = plt.subplot(223)  # Omniwheel errors
    ax4 = plt.subplot(224)  # Ball rotation errors
    
    # Set titles and labels
    ax1.set_title('Omniwheel Angular Velocities')
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Angular Velocity (rad/s)')
    
    ax2.set_title('Ball Angular Velocities')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Angular Velocity (rad/s)')
    
    ax3.set_title('Omniwheel Error')
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Error (rad/s)')
    
    ax4.set_title('Ball Rotation Error')
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Error (rad/s)')
    
    plt.tight_layout()
    return fig, (ax1, ax2, ax3, ax4)

def updatePlots(data_buffer, fig, axes):
    """
    Update all plots with dynamic scaling
    """
    ax1, ax2, ax3, ax4 = axes
    time_vector = data_buffer.get_time_vector()
    
    if len(time_vector) < 2:
        return

    # Clear all plots
    for ax in axes:
        ax.clear()

    # Colors for the three components
    colors = ['red', 'green', 'blue']
    
    try:
        # Plot omniwheel velocities (ax1)
        y_max_ax1 = 0
        for i in range(3):
            setpoints = np.array([x[i] for x in data_buffer.data['setpoint_omni']])
            feedback = np.array([x[i] for x in data_buffer.data['feedback_omni']])
            ax1.plot(time_vector, setpoints, '--', color=colors[i], label=f'Setpoint {i+1}')
            ax1.plot(time_vector, feedback, '-', color=colors[i], label=f'Feedback {i+1}')
            y_max_ax1 = max(y_max_ax1, np.max(np.abs(setpoints)), np.max(np.abs(feedback)))

        # Plot ball velocities (ax2)
        y_max_ax2 = 0
        for i in range(3):
            setpoints = np.array([x[i] for x in data_buffer.data['setpoint_ball']])
            feedback = np.array([x[i] for x in data_buffer.data['feedback_ball']])
            ax2.plot(time_vector, setpoints, '--', color=colors[i], label=f'Setpoint axis {i+1}')
            ax2.plot(time_vector, feedback, '-', color=colors[i], label=f'Feedback axis {i+1}')
            y_max_ax2 = max(y_max_ax2, np.max(np.abs(setpoints)), np.max(np.abs(feedback)))

        # Plot omniwheel errors (ax3)
        y_max_ax3 = 0
        for i in range(3):
            errors = np.array([x[i] for x in data_buffer.data['omni_error']])
            ax3.plot(time_vector, errors, '-', color=colors[i], label=f'Wheel {i+1} Error')
            y_max_ax3 = max(y_max_ax3, np.max(np.abs(errors)))

        # Plot ball rotation errors (ax4)
        y_max_ax4 = 0
        for i in range(3):
            errors = np.array([x[i] for x in data_buffer.data['ball_error']])
            ax4.plot(time_vector, errors, '-', color=colors[i], label=f'Axis {i+1} Error')
            y_max_ax4 = max(y_max_ax4, np.max(np.abs(errors)))

        # Set axis limits with padding
        padding = 1.1  # 10% padding
        for ax, y_max in zip(axes, [y_max_ax1, y_max_ax2, y_max_ax3, y_max_ax4]):
            if y_max > 0:
                ax.set_ylim(-y_max * padding, y_max * padding)
            ax.set_xlim(-data_buffer.buffer_duration, 0)  # Time axis from -buffer_duration to 0
            ax.grid(True)
            ax.legend()

        # Update titles and labels
        ax1.set_title('Omniwheel Angular Velocities')
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Angular Velocity (rad/s)')

        ax2.set_title('Ball Angular Velocities')
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Angular Velocity (rad/s)')

        ax3.set_title('Omniwheel Error')
        ax3.set_xlabel('Time (s)')
        ax3.set_ylabel('Error (rad/s)')

        ax4.set_title('Ball Rotation Error')
        ax4.set_xlabel('Time (s)')
        ax4.set_ylabel('Error (rad/s)')

        plt.tight_layout()
        
        # Use non-blocking draw and flush
        fig.canvas.draw_idle()
        fig.canvas.flush_events()
        
    except Exception as e:
        print(f"Error in plotting: {str(e)}")
        raise

def pidController(error, integral, lastError, dt):
    """
    PID controller implementation
    """
    integral = integral + error * dt
    derivative = (error - lastError) / dt
    
    output = kP * error + kI * integral + kD * derivative
    
    return output, integral

def mainControlLoop():
    # Calculate Jacobian matrices (constant for fixed geometry)
    jacobInv, jacob = jacobian(
        ballRot=np.zeros(3),
        beta=beta,
        rBall=rBall,
        rOmni=rOmni,
        rZ=rZ,
        rX=rX
    )

    # Initialize PID variables
    integral = np.zeros(3)
    lastError = np.zeros(3)

    # Initialize plotting
    fig, axes = initializePlots()
    data_buffer = DataBuffer(BUFFER_DURATION, SAMPLE_TIME)
    last_plot_update = time.time()

    try:
        while True:
            current_time = time.time()
            
            # Get desired ball rotation
            setpointBallAngVel = generateSetpointBallAngVel()

            # Get encoder feedback
            encoderOmniAngVel = getOmniEncoder()

            # Calculate actual ball rotation from feedback
            feedbackBallAngVel = calculateBallAngVelFeedback(encoderOmniAngVel, jacob)

            # Calculate errors
            ballAngVelError = setpointBallAngVel - feedbackBallAngVel

            # Apply PID control
            pidOutput = np.zeros(3)
            for i in range(3):
                pidOutput[i], integral[i] = pidController(
                    ballAngVelError[i],
                    integral[i],
                    lastError[i],
                    SAMPLE_TIME
                )
            lastError = ballAngVelError

            # Add PID output to desired rotation
            correctedBallAngVel = setpointBallAngVel + pidOutput

            # Calculate desired omniwheel velocities
            setpointOmniAngVel = omniAngVel(
                setpointBallAngVel=correctedBallAngVel,
                jacobInv=jacobInv
            )

            # Send setpoints to motor controller
            sendSetpointAngVel(setpointOmniAngVel)

            # Store data
            data_buffer.add_data(
                timestamp=current_time,
                setpoint_omni=setpointOmniAngVel,
                feedback_omni=encoderOmniAngVel,
                omni_error=setpointOmniAngVel - encoderOmniAngVel,
                setpoint_ball=setpointBallAngVel,
                feedback_ball=feedbackBallAngVel,
                ball_error=ballAngVelError
            )

            # Update plots every second
            if current_time - last_plot_update >= 1.0:
                updatePlots(data_buffer, fig, axes)
                last_plot_update = current_time

            time.sleep(SAMPLE_TIME)

    except KeyboardInterrupt:
        print("Control loop terminated by user")
        plt.ioff()
        plt.close('all')

def testRun():
    """
    Test run with simulated values and feedback
    """
    # Calculate Jacobian matrices (constant for fixed geometry)
    jacobInv, jacob = jacobian(
        ballRot=np.zeros(3),
        beta=beta,
        rBall=rBall,
        rOmni=rOmni,
        rZ=rZ,
        rX=rX
    )

    # Initialize PID variables
    integral = np.zeros(3)
    lastError = np.zeros(3)

    # Initialize plotting with non-blocking mode
    plt.ion()  # Enable interactive mode
    fig, axes = initializePlots()
    data_buffer = DataBuffer(BUFFER_DURATION, SAMPLE_TIME)
    last_plot_update = time.time()

    # Initialize test signal generator
    test_gen = TestSignalGenerator(SAMPLE_TIME, TEST_LAG_MULTIPLIER, ERROR_PERCENTAGE)

    running = True
    print("Press Ctrl+C to stop the test...")
    
    try:
        while running:
            try:
                current_time = time.time()
                
                # Generate test setpoint for ball rotation
                setpointBallAngVel = test_gen.generate_setpoint()

                # Calculate desired omniwheel velocities
                setpointOmniAngVel = omniAngVel(
                    setpointBallAngVel=setpointBallAngVel,
                    jacobInv=jacobInv
                )

                # Generate simulated encoder feedback with lag and error
                encoderOmniAngVel = test_gen.generate_feedback()
                
                # Calculate actual ball rotation from feedback
                feedbackBallAngVel = calculateBallAngVelFeedback(encoderOmniAngVel, jacob)

                # Calculate errors
                ballAngVelError = setpointBallAngVel - feedbackBallAngVel
                omniAngVelError = setpointOmniAngVel - encoderOmniAngVel

                # Store data
                data_buffer.add_data(
                    timestamp=current_time,
                    setpoint_omni=setpointOmniAngVel,
                    feedback_omni=encoderOmniAngVel,
                    omni_error=omniAngVelError,
                    setpoint_ball=setpointBallAngVel,
                    feedback_ball=feedbackBallAngVel,
                    ball_error=ballAngVelError
                )

                # Update plots every second
                if current_time - last_plot_update >= 1.0:
                    updatePlots(data_buffer, fig, axes)
                    last_plot_update = current_time

                time.sleep(SAMPLE_TIME)

            except KeyboardInterrupt:
                print("\nStopping test run...")
                running = False
                break

    finally:
        print("Cleaning up...")
        plt.ioff()
        plt.close('all')

if __name__ == "__main__":
    # Set TEST_MODE to True for test run, False for regular operation
    TEST_MODE = True
    
    try:
        if TEST_MODE:
            print("Starting test run with simulated values...")
            testRun()
        else:
            print("Starting regular operation...")
            mainControlLoop()
    except Exception as e:
        print(f"Error occurred: {str(e)}")
    finally:
        plt.ioff()
        plt.close('all')
        print("Program terminated.")






