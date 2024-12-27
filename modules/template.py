def debug_set_dac(dac_num=[], Value=0.1, pulsewidth=1):

    return 

def debug_read_adc(gain=0, samplingPoints=50,ch=1,delay=1):
    return 




def read_one(row=1, col=1, Vread=0.1, numPoint=50):
    return 

def read_16(row=1, col=[], Vread=0.1, numPoint=50):
    return

def compute_byte_16(row=[], col=[], Vread=0.1, pulseWidth=1e-5, numPoint=50):
    return

def compute_byte_all(row=[], Vread=0.1, pulseWidth=1e-5, numPoint=50):

    while 1:
        compute_byte_16(x) 
    return

def write_one_dG(row=1, col=1, Vwrite=5, pulsewidth=0.1, dG=1e-3, dGperPulse=1e-5, eRate=0.01, maxWrite=10):
    # PWM
    # PNM
    # open loop; closed loop.
    return

def write_one_targetG(row=1, col=1, Vwrite=5, pulsewidth=0.1, target_G=1e-3, dGperPulse=1e-5, eRate=0.01, maxWrite=10):

    # PWM
    # PNM
    # open loop; closed loop.
    #1T1R CC
    return

# def write_parallel_col(row=[], col=1, Vwrite=5, pulsewidth=0.1, target_G=[], dGperPulse=1e-5, eRate=0.01, maxWrite=10):
#     return
