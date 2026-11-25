// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S3.1-01)
// ============================================================================
// part_id           : S3.1-01
// parent_bom_id     : S3.1
// subsystem         : S3
// part_name         : Pikselli p-i-n diyot IBIC algilama katmanli substrat tasiyici
// material          : Si
// temp_stage        : 4 K - 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.05 pF
// computed_mass_kg  : 0.00233
// envelope_mm       : 50.000 x 50.000 x 0.525
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 50.0000;
bbox_y = 50.0000;
bbox_z = 0.5250;

// Part-specific parametric dimensions
wafer_od_mm = 50.0;
wafer_thickness_mm = 0.525;
active_field_mm = 16.0;
guard_moat_r_in_mm = 20.0;
guard_moat_r_out_mm = 22.6;

// Interface / port parameters (mm)
port_active_implant_plane_od = 50.000;
port_wafer_pocket_seat_od = 50.000;

module part_S3_1_01() {
  union() {
    // Ø50x0.525 mm high-res Si p-i-n IBIC wafer w/ guard-ring moat
    rotate_extrude(angle=360) polygon(points=[[0.0000, -0.2625], [25.0000, -0.2625], [25.0000, 0.2625], [22.6000, 0.2625], [22.6000, 0.1825], [20.0000, 0.1825], [20.0000, 0.2625], [0.0000, 0.2625]]);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -0.263]) rotate([0.000, 0.000, 0.000]) part_S3_1_01();

part_S3_1_01();
