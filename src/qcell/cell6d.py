#!/usr/bin/env python3
"""
6D Programmable Self-Replicating Cell
======================================

A unified 6-dimensional field theory combining:
1. Phase field (φ) - cell morphology (Cahn-Hilliard)
2. Chemical fuel (c) - energy metabolism
3. Electric field (E) - electrostatic control
4. Memory state (m) - information storage
5. Program state (p) - instruction execution
6. Replication clock (r) - division timing

Based on:
- Zwicker et al. (2017) active droplets
- Cahn-Hilliard / Ohta-Kawasaki phase-field
- Gray-Scott reaction-diffusion
- LJ cluster physics with gate-screened Coulomb
- SKY130 2D electron gas energetics
"""

import numpy as np
from scipy import fft as sfft
from scipy import ndimage


class Cell6D:
    """
    6D Cell with programmable self-replication.
    
    Dimensions (internal degrees of freedom):
    0: φ (phi) - phase field / cell morphology
    1: c (chem) - chemical fuel concentration
    2: E (elec) - electric field
    3: m (mem) - memory/information state
    4: p (prog) - program counter state
    5: r (rep) - replication clock
    
    All fields live on 3D spatial grid (n, n, n).
    """
    
    def __init__(self, n=32, L=32.0, R=8.0, seed=0):
        self.n = n
        self.L = L
        self.dx = L / n
        self.R0 = R
        self.rng = np.random.default_rng(seed)
        
        # 3D spatial grid
        x = (np.arange(n) + 0.5) * self.dx
        X = np.meshgrid(*([x] * 3), indexing='ij')
        self.X = np.array(X)  # (3, n, n, n)
        
        # Fourier space (3D)
        freqs = [2 * np.pi * np.fft.fftfreq(n, d=self.dx)] * 2 + \
                [2 * np.pi * np.fft.rfftfreq(n, d=self.dx)]
        grids = np.meshgrid(*freqs, indexing='ij')
        self.q2 = sum(g**2 for g in grids)
        self.q = np.sqrt(self.q2)
        self.q[0, 0, 0] = 1.0
        
        # Fields - all shape (n, n, n)
        shape = (n, n, n)
        self.phi = np.zeros(shape, dtype=np.float64)      # phase field
        self.chem = np.zeros(shape, dtype=np.float64)     # chemical fuel
        self.elec = np.zeros(shape, dtype=np.float64)     # electric field
        self.mem = np.zeros(shape, dtype=np.float64)      # memory
        self.prog = np.zeros(shape, dtype=np.float64)     # program state
        self.rep = np.zeros(shape, dtype=np.float64)      # replication clock
        
        # Program field: 6 internal dims x 3D spatial
        self.prog_field = np.zeros((6, n, n, n), dtype=np.float64)
        self.prog_instructions = []
        self.prog_idx = 0
        self.prog_timer = 0.0
        
        # Physical parameters (carefully tuned for stability)
        # Cahn-Hilliard parameters (from exp8, exp11)
        self.kappa = 0.25       # interface energy coefficient
        self.A_coul = 0.1       # Coulomb strength (gate-screened)
        self.d_gate = 2.0       # gate screening distance
        self.M = 1.0            # mobility
        self.S = 2.0            # stabilizer for semi-implicit
        
        # Chemical kinetics
        self.D_chem = 0.01      # diffusion (slow)
        self.nu_prod = 0.005    # production rate
        self.nu_deg = 0.001     # degradation rate
        
        # Electric coupling
        self.gate_coupling = 0.1
        
        # Replication
        self.rep_threshold = 0.8
        self.rep_rate = 0.005
        self.divide_frac = 0.4
        
        # Coulomb kernel (gate-screened)
        self.g_kernel = np.zeros_like(self.q)
        nz = self.q > 0
        self.g_kernel[nz] = self.A_coul * (-np.expm1(-2 * self.q[nz] * self.d_gate)) / self.q[nz]
        
        # Linear operator for semi-implicit Cahn-Hilliard
        self.lin_op = self.M * self.q2 * (self.S + self.g_kernel) + 0.25 * self.q2**2
        self.denom = None
        
        # Tracking
        self.trajectory = []
        self.replication_events = 0
        self.division_events = 0
        self.death_events = 0
        self.energy_consumed = 0.0
        self._last_n = 1
        
    def disk(self, R, center=None, c_out=0.0):
        """Initialize droplet with tanh interface."""
        ctr = [self.L / 2] * 3 if center is None else center
        rho = np.sqrt(sum((((Xi - ci + self.L / 2) % self.L - self.L / 2)) ** 2 
                         for Xi, ci in zip(self.X, ctr))) / R
        return c_out + (1.0 - c_out) * 0.5 * (1 - np.tanh((rho - 1.0) * R))
    
    def _free_energy_derivative(self, phi):
        """δF/δφ = -φ + φ³ - κ∇²φ + Coulomb term (handled in Fourier)."""
        # Bulk: -φ + φ³ = φ(φ² - 1) = -(φ - φ³) = -(φ(1-φ²))
        # Using double-well potential: f(φ) = (φ²-1)²/4, f'(φ) = φ(φ²-1)
        return phi * (phi**2 - 1.0)
    
    def _chem_reaction(self, chem, phi):
        """Chemical fuel reaction: production inside, decay outside."""
        # Production where cell exists (phi > 0)
        # Saturating production, linear decay
        prod = self.nu_prod * phi * (1.0 - chem)
        deg = self.nu_deg * chem
        return prod - deg
    
    def _division_dynamics(self, phi, rep):
        """Division dynamics: replication clock advances, then splits."""
        # Clock advances in high-phi, high-fuel regions
        clock_advance = self.rep_rate * self.chem * np.clip(phi, 0, 1)
        new_rep = rep + clock_advance
        
        # Division when clock exceeds threshold
        divide_mask = (new_rep > self.rep_threshold) & (phi > 0.5)
        if np.any(divide_mask):
            # Split by reducing phi and creating perturbation
            phi = phi.copy()
            phi[divide_mask] *= (1.0 - self.divide_frac)
            # Add small random perturbation to break symmetry
            noise = self.rng.normal(0, 0.05, phi.shape)
            phi += noise * divide_mask
            phi = np.clip(phi, -1.0, 2.0)
            new_rep[divide_mask] = 0.0
            self.division_events += 1
        
        return phi, new_rep
    
    def _memory_update(self, mem, phi):
        """Memory: leaky integrator of phi."""
        return 0.995 * mem + 0.005 * phi
    
    def load_program(self, prog_field):
        """Load compiled program field."""
        self.prog_field = prog_field
        self.prog_idx = 0
        self.prog_timer = 0.0
    
    def step(self, dt, E_ext=None):
        """Single time step - semi-implicit Cahn-Hilliard + reactions."""
        # Update denominator
        self.denom = 1.0 + dt * self.lin_op
        
        # 1. PHASE FIELD (Cahn-Hilliard with Coulomb)
        # Nonlinear bulk derivative
        f_prime = self._free_energy_derivative(self.phi)
        
        # External field coupling
        E_term = np.zeros_like(self.phi)
        if E_ext is not None:
            E_term = self.gate_coupling * E_ext[0]
        
        # Fourier space
        ch = sfft.rfftn(self.phi)
        fh = sfft.rfftn(f_prime)
        Eh = sfft.rfftn(E_term)
        
        # Semi-implicit: ∂ₜφ = M ∇²(δF/δφ) + E_coupling
        # In Fourier: ∂ₜφ̂ = -M q² (f̂ + κ q² φ̂ + G φ̂) + Ê
        rhs = ch - dt * self.M * self.q2 * (fh + self.kappa * self.q2 * ch + self.g_kernel * ch) + dt * Eh
        
        ch_new = rhs / self.denom
        self.phi = sfft.irfftn(ch_new, s=self.phi.shape)
        self.phi = np.clip(self.phi, -1.5, 1.5)  # Stability clipping
        
        # 2. CHEMICAL FUEL (reaction-diffusion)
        reaction = self._chem_reaction(self.chem, self.phi)
        self.chem += dt * (self.D_chem * self._laplacian(self.chem) + reaction)
        self.chem = np.clip(self.chem, 0.0, 2.0)
        
        # 3. MEMORY (leaky integration)
        self.mem = self._memory_update(self.mem, self.phi)
        self.mem = np.clip(self.mem, -1.0, 1.0)
        
        # 4. REPLICATION CLOCK & DIVISION
        self.phi, self.rep = self._division_dynamics(self.phi, self.rep)
        
        # 5. PROGRAM EXECUTION
        if self.prog_instructions and self.prog_idx < len(self.prog_instructions):
            self._execute_instruction()
        
        # 6. ENERGY ACCOUNTING
        grad = np.gradient(self.phi)
        grad_sq = sum(g**2 for g in grad)
        self.energy_density = 0.25 * (self.phi**2 - 1.0)**2 + 0.125 * grad_sq
        self.energy_consumed += dt * np.sum(self.chem * np.clip(self.phi, 0, 1))
        
        # Tracking
        if len(self.trajectory) % 10 == 0:
            drops = self.droplets(self.phi)
            if drops['centres']:
                self.trajectory.append({
                    't': len(self.trajectory) * dt,
                    'centres': drops['centres'],
                    'n_drops': drops['n']
                })
    
    def _execute_instruction(self):
        """Execute current program instruction."""
        instr = self.prog_instructions[self.prog_idx]
        op = instr['op']
        params = instr['params']
        
        if op == "GROW":
            # Growth in direction of params[0:3]
            growth = 0.02 * sum(params[i] * self.X[i] for i in range(3))
            self.phi += growth
        elif op == "DIVIDE":
            self.rep += 0.05 * (self.phi > 0.3)
        elif op == "STEER":
            steer = 0.01 * sum(params[i] * self.X[i] for i in range(3))
            self.elec += steer
        elif op == "REPLICATE":
            self.rep += 0.02 * (self.phi > 0.2)
        elif op == "IDLE":
            pass
        
        self.prog_timer += 1.0
        if self.prog_timer >= instr['duration']:
            self.prog_idx += 1
            self.prog_timer = 0.0
    
    def _laplacian(self, field):
        """3D periodic Laplacian."""
        return (np.roll(field, 1, 0) + np.roll(field, -1, 0) +
                np.roll(field, 1, 1) + np.roll(field, -1, 1) +
                np.roll(field, 1, 2) + np.roll(field, -1, 2) - 6 * field) / self.dx**2
    
    def run(self, T, dt=0.05, E_ext_func=None, store_every=100):
        """Run simulation for time T."""
        n_steps = int(round(T / dt))
        store_every = max(1, store_every)
        
        for i in range(n_steps):
            t = i * dt
            E_ext = E_ext_func(t) if E_ext_func else None
            self.step(dt, E_ext)
            
            if i % store_every == 0:
                drops = self.droplets(self.phi)
                if drops['n'] != self._last_n:
                    if drops['n'] > self._last_n:
                        self.replication_events += drops['n'] - self._last_n
                    self._last_n = drops['n']
        
        return {
            'energy_consumed': float(self.energy_consumed),
            'replication_events': self.replication_events,
            'division_events': self.division_events,
            'death_events': self.death_events,
            'trajectory': self.trajectory,
            'final_phi': self.phi.copy(),
            'final_chem': self.chem.copy()
        }
    
    def droplets(self, phi, thr=0.5, r_min=1.0):
        """Detect droplets in 3D."""
        n = self.n
        big = np.tile(phi > thr, (3, 3, 3))
        lab, k = ndimage.label(big)
        if k == 0:
            return {'n': 0, 'radii': [], 'centres': [], 'perc': False}
        
        idx = range(1, k + 1)
        com = ndimage.center_of_mass(big, lab, idx)
        size = ndimage.sum(big, lab, idx)
        slices = ndimage.find_objects(lab)
        
        radii, centres = [], []
        for i in range(k):
            if not all(n <= x < 2 * n for x in com[i]):
                continue
            vol = size[i] * self.dx**3
            r = float((3 * vol / (4 * np.pi)) ** (1/3))
            if r >= r_min:
                radii.append(r)
                centres.append([float(c - n) for c in com[i]])
        
        return {'n': len(radii), 'radii': radii, 'centres': centres, 'perc': False}
    
    def add_instruction(self, op, params, duration):
        """Add instruction to program."""
        self.prog_instructions.append({'op': op, 'params': params, 'duration': duration})


class Program6D:
    """6D Program compiler - converts instructions to field."""
    
    def __init__(self):
        self.instructions = []
    
    def add_instruction(self, op, params, duration):
        self.instructions.append({'op': op, 'params': params, 'duration': duration})
    
    def compile(self, n, L):
        """Compile program to 6D field (6, n, n, n)."""
        prog = np.zeros((6, n, n, n))
        for i, instr in enumerate(self.instructions):
            params = instr['params']
            for d in range(6):
                prog[d] += params[d] * (i + 1) if d < len(params) else 0
        return prog


def run_6d_simulation(config):
    """Run 6D simulation with config dict."""
    cell = Cell6D(
        n=config.get('n', 32),
        L=config.get('L', 32.0),
        R=config.get('R', 8.0),
        seed=config.get('seed', 0)
    )
    
    cell.phi[:] = cell.disk(R=config.get('R', 8.0))
    cell.chem[:] = config.get('fuel', 0.5)
    
    if 'program' in config:
        prog = Program6D()
        for instr in config['program']:
            prog.add_instruction(instr['op'], instr['params'], instr['duration'])
        cell.load_program(prog.compile(cell.n, cell.L))
        cell.prog_instructions = prog.instructions
    
    E_ext_func = config.get('E_ext_func', None)
    
    result = cell.run(
        T=config.get('T', 500.0),
        dt=config.get('dt', 0.02),  # Smaller dt for stability
        E_ext_func=E_ext_func,
        store_every=config.get('store_every', 200)
    )
    
    return cell, result


if __name__ == "__main__":
    cell, result = run_6d_simulation({
        'n': 32, 'L': 32.0, 'R': 8.0, 'seed': 42,
        'fuel': 0.5, 'T': 100.0
    })
    
    drops = cell.droplets(cell.phi)
    print(f"Test run: {drops['n']} droplets, radii={drops['radii']}")
    print(f"Energy consumed: {result['energy_consumed']:.4f}")
    print(f"Replications: {result['replication_events']}")