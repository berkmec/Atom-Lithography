// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S3.2-04)
// ============================================================================
// part_id           : S3.2-04
// parent_bom_id     : S3.2
// subsystem         : S3
// part_name         : Kisa (<5 cm) vakum-ici mikro-koaksiyel IBIC sinyal demeti (Exp127)
// material          : PTFE
// temp_stage        : 4 K - 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±2 mm boy
// computed_mass_kg  : 0.00544
// envelope_mm       : 156.882 x 157.923 x 11.436
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 156.8825;
bbox_y = 157.9225;
bbox_z = 11.4360;

// Part-specific parametric dimensions
n_looms = 16;
arc_length_mm = 44.76;
bundle_od_mm = 1.7;
max_stray_pf = 0.15;

// Interface / port parameters (mm)
port_wafer_ring_launch_bore = 84.400;
port_csa_100k_input_od = 169.600;

module part_S3_2_04() {
  union() {
    // Micro-coax IBIC loom #1 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([58.876, 23.788, -3.500]) rotate([0.000, 77.000, 22.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #2 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([52.016, 36.422, -3.500]) rotate([0.000, 77.000, 35.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #3 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([33.650, 53.851, -3.500]) rotate([0.000, 77.000, 58.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #4 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([21.718, 59.670, -3.500]) rotate([0.000, 77.000, 70.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #5 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([-25.828, 58.010, -3.500]) rotate([0.000, 77.000, 114.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #6 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([-39.095, 50.039, -3.500]) rotate([0.000, 77.000, 128.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #7 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([-50.039, 39.095, -3.500]) rotate([0.000, 77.000, 142.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #8 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([-58.010, 25.828, -3.500]) rotate([0.000, 77.000, 156.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #9 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([-58.010, -25.828, -3.500]) rotate([0.000, 77.000, 204.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #10 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([-50.039, -39.095, -3.500]) rotate([0.000, 77.000, 218.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #11 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([-39.095, -50.039, -3.500]) rotate([0.000, 77.000, 232.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #12 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([-25.828, -58.010, -3.500]) rotate([0.000, 77.000, 246.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #13 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([25.828, -58.010, -3.500]) rotate([0.000, 77.000, 294.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #14 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([39.095, -50.039, -3.500]) rotate([0.000, 77.000, 308.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #15 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([50.039, -39.095, -3.500]) rotate([0.000, 77.000, 322.000]) cylinder(d=1.700, h=44.760, center=true);
    // Micro-coax IBIC loom #16 (L=44.76 mm < 50 mm, C_par<0.15 pF)
    translate([58.010, -25.828, -3.500]) rotate([0.000, 77.000, 336.000]) cylinder(d=1.700, h=44.760, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 0.000]) rotate([0.000, 0.000, 0.000]) part_S3_2_04();

part_S3_2_04();
