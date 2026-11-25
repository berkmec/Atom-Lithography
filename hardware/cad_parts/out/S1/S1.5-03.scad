// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.5-03)
// ============================================================================
// part_id           : S1.5-03
// parent_bom_id     : S1.5
// subsystem         : S1
// part_name         : Enerji suzgeci ultra-dusuk gurultulu cift-kutuplu besleme
// material          : Al 6061
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : ±50 mV
// computed_mass_kg  : 5.35001
// envelope_mm       : 482.600 x 442.500 x 42.450
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 442.5000;
bbox_z = 42.4500;

// Part-specific parametric dimensions
rack_u = 1;
u_slot = "U31";
ripple_mVpp = 50.0;
stability_ppm = 10.0;

// Interface / port parameters (mm)
port_hda_hemi_bias_out_od = 14.000;

module part_S1_5_03() {
  difference() {
    union() {
      // 1U hollow 19-in chassis body (width along X)
      translate([0.000, 9.500, 0.000]) cube([440.000, 411.000, 42.450], center=true);
      // EIA-310 19-in front panel w/ mounting ears facing -Y
      translate([0.000, -198.500, 0.000]) cube([482.600, 5.000, 42.450], center=true);
    }
    // EIA-310 +X rack slot
    translate([232.550, -198.500, 0.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.400, h=9.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.400, h=9.000, center=true);
      }
    }
    // EIA-310 -X rack slot
    translate([-232.550, -198.500, 0.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.900, 0, 0]) cylinder(d=6.400, h=9.000, center=true);
        translate([1.900, 0, 0]) cylinder(d=6.400, h=9.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([1480.000, -223.000, 945.725]) rotate([0.000, 0.000, 0.000]) part_S1_5_03();

part_S1_5_03();
