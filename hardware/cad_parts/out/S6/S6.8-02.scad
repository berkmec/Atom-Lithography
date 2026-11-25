// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.8-02)
// ============================================================================
// part_id           : S6.8-02
// parent_bom_id     : S6.8
// subsystem         : S6
// part_name         : Kapali-cevrim 3He/4He gaz isleme sistemi (GHS), turbo sirkulasyon ve soguk kapanlar
// material          : 316L
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Kapali 3He/4He dongu
// tolerance         : He <=1e-10 mbar*L/s
// computed_mass_kg  : 169.85068
// envelope_mm       : 600.000 x 560.000 x 1662.200
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 600.0000;
bbox_y = 560.0000;
bbox_z = 1662.2000;

// Part-specific parametric dimensions
ghs_w = 600.0;
ghs_d = 560.0;
ghs_h = 1650.0;
he3_stp_l = 20.0;

// Interface / port parameters (mm)
port_still_pumping_line_od = 75.000;
port_still_pumping_line_bore = 50.000;
port_still_pumping_line_bolts = 4;
port_condensing_return_line_od = 75.000;
port_condensing_return_line_bore = 50.000;
port_condensing_return_line_bolts = 4;

module part_S6_8_02() {
  union() {
    // Closed-loop 3He/4He GHS cabinet
    cube([600.000, 560.000, 1650.000], center=true);
    // ISO-K DN50 still pump port
    translate([-120.000, 0.000, 831.200]) cylinder(d=75.000, h=12.000, center=true);
    // ISO-K DN50 condense return port
    translate([120.000, 0.000, 831.200]) cylinder(d=75.000, h=12.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-1300.000, -800.000, 825.000]) rotate([0.000, 0.000, 0.000]) part_S6_8_02();

part_S6_8_02();
