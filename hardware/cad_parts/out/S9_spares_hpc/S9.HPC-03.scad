// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S9.HPC-03)
// ============================================================================
// part_id           : S9.HPC-03
// parent_bom_id     : S9.HPC
// subsystem         : S9
// part_name         : Yedekli 2.6 kW Titanium PSU Paketi, Surgulu Raf Raylari & ZU48DR 100G CMAC RDMA Entegrasyon Kiti (Exp143, 3.80 kg)
// material          : Steel
// temp_stage        : 300 K (HPC rafi)
// vacuum_grade      : Atmosfer
// tolerance         : 99.99% yedekli PSU
// computed_mass_kg  : 3.80000
// envelope_mm       : 556.000 x 780.000 x 365.200
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 556.0000;
bbox_y = 780.0000;
bbox_z = 365.2000;

// Part-specific parametric dimensions
psu_kw = 2.6;
rail_depth_mm = 780.0;
om4_bend_r_mm = 45.0;

// Interface / port parameters (mm)
port_om4_fiber_duct_entry_od = 28.000;
port_om4_fiber_duct_entry_bore = 18.000;

module part_S9_HPC_03() {
  union() {
    // 2.6 kW redundant Titanium PSU plinth
    translate([0.000, 0.000, -142.500]) cube([520.000, 780.000, 80.000], center=true);
    // Left sliding rail assembly
    translate([-256.000, 0.000, 40.000]) cube([16.000, 780.000, 285.000], center=true);
    // Right sliding rail assembly
    translate([256.000, 0.000, 40.000]) cube([16.000, 780.000, 285.000], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([2750.000, -700.000, 182.500]) rotate([0.000, 0.000, 0.000]) part_S9_HPC_03();

part_S9_HPC_03();
