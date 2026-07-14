import numpy as np
import matplotlib.pyplot as plt
import cmath as cm
import pandas as pd

plt.rcParams.update({'font.size': 14})

# Constants
g0      = 9.81    # m/s^2
density = 1.225   # kg/m^3

# AIRCRAFT PROPERTIES
# Mass and Inertias
mass   = 1.35            # kg
Ix     = 0.15            # kg*m^2
Iy     = 0.35            # kg*m^2
Iz     = 0.45            # kg*m^2
Ixz    = 0.00            # kg*m^2

# Reference Geometry
S_ref = 0.171            # m^2 (Reference Area)
c_ref = 0.22             # m   (Reference Chord)
b_ref = 1.2              # m   (Reference Span)

# Trim Conditions
Vtrim = 20.0             # m/s
alpha_trim_deg = 4.5     # deg
theta0 = alpha_trim_deg * np.pi / 180.0
Q = 0.5 * density * Vtrim**2

# AERODYNAMIC COEFFICIENTS
def get_deriv(col_name):
    return np.interp(Vtrim, vel_data, df_stab[col_name].values)

# Base Coefficients at Trim
CL0 = 0.450
CD0 = 0.025
CM0 = 0.000

# Hardcoded Derivatives
CLa = 4.500     # CL_alpha
CDa = 0.200     # CD_alpha
CMa = -0.800    # Cm_alpha
CLq = 6.000     # CL_q
CDq = 0.000     # CD_q

# Lateral Derivatives
df_stab = pd.read_csv('databases/stability.csv')
vel_data = df_stab['Velocity'].values
CMq = get_deriv('Cm_q')
CYb = get_deriv('CY_beta')
Clb = get_deriv('Cl_beta')
Cnb = get_deriv('Cn_beta')
CYp = get_deriv('CY_p')
Clp = get_deriv('Cl_p')
Cnp = get_deriv('Cn_p')
CYr = get_deriv('CY_r')
Clr = get_deriv('Cl_r')
Cnr = get_deriv('Cn_r')

# DIMENSIONAL DERIVATIVES
# Longitudinal Dimensional Derivatives
# X-force
XU = -(Q * S_ref * (2.0 * CD0)) / (mass * Vtrim)
XW =  (Q * S_ref * (CL0 - CDa)) / (mass * Vtrim)
XQ = -(Q * S_ref * c_ref * CDq) / (2.0 * mass * Vtrim)

# Z-force
ZU = -(Q * S_ref * (2.0 * CL0)) / (mass * Vtrim)
ZW = -(Q * S_ref * (CLa + CD0)) / (mass * Vtrim)
ZQ = -(Q * S_ref * c_ref * CLq) / (2.0 * mass * Vtrim)
ZWDOT = 0.0

# Pitching Moment
MU = 0.0 
MW =  (Q * S_ref * c_ref * CMa) / (Iy * Vtrim)
MQ =  (Q * S_ref * c_ref**2 * CMq) / (2.0 * Iy * Vtrim)
MWDOT = 0.0

# Lateral Dimensional Derivatives
# Y-force
YV =  (Q * S_ref * CYb) / (mass * Vtrim)
YP =  (Q * S_ref * b_ref * CYp) / (2.0 * mass * Vtrim)
YR =  (Q * S_ref * b_ref * CYr) / (2.0 * mass * Vtrim)

# Rolling Moment
LV =  (Q * S_ref * b_ref * Clb) / (Ix * Vtrim)
LP =  (Q * S_ref * b_ref**2 * Clp) / (2.0 * Ix * Vtrim)
LR =  (Q * S_ref * b_ref**2 * Clr) / (2.0 * Ix * Vtrim)

# Yawing Moment
NV =  (Q * S_ref * b_ref * Cnb) / (Iz * Vtrim)
NP =  (Q * S_ref * b_ref**2 * Cnp) / (2.0 * Iz * Vtrim)
NR =  (Q * S_ref * b_ref**2 * Cnr) / (2.0 * Iz * Vtrim)


# STATE SPACE MATRICES
# Longitudinal A-Matrix (States: u, w, q, theta)
first_row  = [XU, XW, 0, -g0 * np.cos(theta0)]
second_row = [ZU, ZW, Vtrim, -g0 * np.sin(theta0)]
third_row  = [MU + MWDOT * ZU, MW + MWDOT * ZW, MQ + Vtrim * MWDOT, -MWDOT * g0 * np.sin(theta0)]
fourth_row = [0., 0., 1., 0.]
ALON = [first_row, second_row, third_row, fourth_row]

# Approximation to Phugoid
Aph = [[XU, -g0], [-ZU / Vtrim, 0]]
# Approximation to Short Period
Asp = [[ZW / (1 - ZWDOT), (Vtrim + ZQ) / (1 - ZWDOT)],
       [MW + (MWDOT * ZW) / (1 - ZWDOT), MQ + MWDOT * (Vtrim + ZQ) / (1 - ZWDOT)]]

# Create Lateral A-Matrix
first_row  = [YV, YP, g0 * np.cos(theta0), YR - Vtrim]
second_row = [LV, LP, 0., LR]
third_row  = [0., 1., 0., 0.]
fourth_row = [NV, NP, 0., NR]
ALAT = [first_row, second_row, third_row, fourth_row]

# Approximation to Dutch Roll
a = 1.0
b = -((LP * NR + Vtrim * NV - LR * NP) / (LP + NR)
      + Vtrim * (LV * NP - LP * NV) / (LP + NR)**2)
c = Vtrim * (LP * NV - LV * NP) / (LP + NR)
dutch_roll1 = -b / (2 * a) + 0.5 * cm.sqrt(b**2 - 4 * a * c)
dutch_roll2 = -b / (2 * a) - 0.5 * cm.sqrt(b**2 - 4 * a * c)

# Approximation to Roll Mode
ix = Ixz / Ix
iz = Ixz / Iz
roll_mode = (LP + ix * NP) / (1 - ix * iz)

# Approximation to Spiral
spiral_mode = NR - LR * NV / LV

# COMPUTE EIGENVALUES
LONeigenvalues, LONeigenvectors = np.linalg.eig(ALON)
LATeigenvalues, LATeigenvectors = np.linalg.eig(ALAT)
PHeigenvalues,  PHeigenvectors  = np.linalg.eig(Aph)
SPeigenvalues,  PHeigenvectors  = np.linalg.eig(Asp)

# PLOT AND PRINT EVERYTHING
plt.figure(figsize=(10, 6))
plt.axhline(0, color='black', linewidth=1.2, alpha=0.8)
plt.axvline(0, color='black', linewidth=1.2, alpha=0.8)
plt.grid(True, linestyle='--', alpha=0.6)
plt.xlabel('Real Axis')
plt.ylabel('Imaginary Axis')
plt.title('Aircraft Dynamic Modes Root Locus')

print('Longitudinal Modes:')
for i in range(len(LONeigenvalues)):
    print(LONeigenvalues[i])
    # Only label the first point to avoid duplicate legend entries
    lbl = 'Longitudinal Modes' if i == 0 else None
    plt.plot(np.real(LONeigenvalues[i]), np.imag(LONeigenvalues[i]), 'bx', markersize=8, markeredgewidth=2, label=lbl)

print('Short Period Approx:')
for i in range(len(SPeigenvalues)):
    print(SPeigenvalues[i])
    lbl = 'Short Period Approx' if i == 0 else None
    plt.plot(np.real(SPeigenvalues[i]), np.imag(SPeigenvalues[i]), 'rx', markersize=8, markeredgewidth=2, label=lbl)

print('Phugoid Approx:')
for i in range(len(PHeigenvalues)):
    print(PHeigenvalues[i])
    lbl = 'Phugoid Approx' if i == 0 else None
    plt.plot(np.real(PHeigenvalues[i]), np.imag(PHeigenvalues[i]), 'gx', markersize=8, markeredgewidth=2, label=lbl)

print('Lateral Modes:')
for i in range(len(LATeigenvalues)):
    print(LATeigenvalues[i])
    lbl = 'Lateral Modes' if i == 0 else None
    plt.plot(np.real(LATeigenvalues[i]), np.imag(LATeigenvalues[i]), 'bo', markersize=8, label=lbl)

print('Dutch Roll Approx:')
print(dutch_roll1)
plt.plot(np.real(dutch_roll1), np.imag(dutch_roll1), 'ro', markersize=8, label='Dutch Roll Approx')
print(dutch_roll2)
plt.plot(np.real(dutch_roll2), np.imag(dutch_roll2), 'ro', markersize=8)

print('Roll Mode Approx:')
print(roll_mode)
plt.plot(np.real(roll_mode), np.imag(roll_mode), 'go', markersize=8, label='Roll Approx')

print('Spiral Mode Approx:')
print(spiral_mode)
plt.plot(np.real(spiral_mode), np.imag(spiral_mode), 'mo', markersize=8, label='Spiral Approx')

plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left", borderaxespad=0.)
plt.tight_layout()
plt.show()