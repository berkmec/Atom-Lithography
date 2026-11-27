// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.2-02)
// ============================================================================
// part_id           : S5.2-02
// parent_bom_id     : S5.2
// subsystem         : S5
// part_name         : Iyon pompasi (VacIon 75 sinifi) + Titanyum Sublimasyon Pompasi (TSP)
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-10 mbar
// tolerance         : ≤1e-10 mbar
// computed_mass_kg  : 12.64171
// envelope_mm       : 178.000 x 168.500 x 256.800
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 178.0000;
bbox_y = 168.5000;
bbox_z = 256.8000;

// Part-specific parametric dimensions
ion_speed_L_s = 75;
tsp_od_mm = 104.0;
total_h_mm = 256.8;

// Interface / port parameters (mm)
port_tee_cf100_inlet_od = 152.000;
port_tee_cf100_inlet_bore = 101.600;
port_tee_cf100_inlet_pcd = 130.200;
port_tee_cf100_inlet_bolts = 16;
port_tsp_cartridge_top_od = 69.500;
port_tsp_cartridge_top_bore = 38.000;
port_tsp_cartridge_top_pcd = 58.700;
port_tsp_cartridge_top_bolts = 6;

module part_S5_2_02() {
  union() {
    // Bottom CF100 flange mating pump tee
    translate([0.000, 0.000, 9.900]) rotate([180.000, 0.000, 0.000]) {
      difference() {
        cylinder(d=152.000, h=19.800, center=true);
        cylinder(d=101.600, h=21.800, center=true);
        translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
        for (i = [0 : 16 - 1])
          rotate([0, 0, i * 360 / 16])
            translate([65.100, 0, 0])
              cylinder(d=8.400, h=21.800, center=true);
      }
    }
    // 75 L/s VacIon StarCell pump body
    translate([0.000, 0.000, 83.000]) cube([136.000, 116.000, 126.000], center=true);
    // Ferrite magnet + mu-metal shield (-X)
    translate([-79.000, 0.000, 83.000]) cube([20.000, 108.000, 118.000], center=true);
    // Ferrite magnet + mu-metal shield (+X)
    translate([79.000, 0.000, 83.000]) cube([20.000, 108.000, 118.000], center=true);
    // TSP sublimation shroud
    translate([0.000, 0.000, 183.250]) {
      difference() {
        cylinder(d=104.000, h=73.500, center=true);
        cylinder(d=84.000, h=75.500, center=true);
      }
    }
    // Top CF40 3-filament TSP cartridge flange
    translate([0.000, 0.000, 226.400]) {
      difference() {
        cylinder(d=69.500, h=12.700, center=true);
        cylinder(d=38.000, h=14.700, center=true);
        translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
        for (i = [0 : 6 - 1])
          rotate([0, 0, i * 360 / 6])
            translate([29.350, 0, 0])
              cylinder(d=6.600, h=14.700, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, -425.000, 608.300]) rotate([0.000, 0.000, 0.000]) part_S5_2_02();

part_S5_2_02();
