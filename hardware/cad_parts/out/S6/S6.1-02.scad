// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.1-02)
// ============================================================================
// part_id           : S6.1-02
// parent_bom_id     : S6.1
// subsystem         : S6
// part_name         : Uzak doner valf, su sogutmali He kompresoru ve esnek hatlar
// material          : Steel
// temp_stage        : 300 K (tesis)
// vacuum_grade      : 20 bar He
// tolerance         : He 99.999%
// computed_mass_kg  : 150.17445
// envelope_mm       : 480.000 x 520.000 x 680.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 480.0000;
bbox_y = 520.0000;
bbox_z = 680.0000;

// Part-specific parametric dimensions
cpa_w = 480.0;
cpa_d = 520.0;
cpa_h = 680.0;
he_pressure_bar = 20.0;

// Interface / port parameters (mm)
port_he_supply_od = 28.000;
port_he_supply_bore = 16.000;
port_he_return_od = 28.000;
port_he_return_bore = 16.000;
port_chilled_water_in_od = 28.000;
port_chilled_water_in_bore = 12.700;
port_chilled_water_out_od = 28.000;
port_chilled_water_out_bore = 12.700;

module part_S6_1_02() {
  union() {
    // CPA water-cooled He compressor cabinet
    translate([0.000, 0.000, 10.000]) cube([480.000, 520.000, 660.000], center=true);
    // He HP supply coupling
    translate([-120.000, 0.000, 334.000]) cylinder(d=28.000, h=12.000, center=true);
    // He LP return coupling
    translate([-60.000, 0.000, 334.000]) cylinder(d=28.000, h=12.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-1950.000, -800.000, 340.000]) rotate([0.000, 0.000, 0.000]) part_S6_1_02();

part_S6_1_02();
