// Direct ISIS C++ benchmark executable for PyISIS comparison.

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include <QString>

#include "Camera.h"
#include "ControlMeasure.h"
#include "ControlNet.h"
#include "ControlPoint.h"
#include "Cube.h"
#include "IException.h"
#include "UniversalGroundMap.h"

namespace {

struct Options {
  std::string mode;
  std::string label;
  std::string cube_path;
  std::string dom_path;
  std::string original_path;
  std::string net_path;
  std::string output_path;
  int sample_step = 10;
  int line_step = 10;
  int max_points = 0;
  int point_count = 1000000;
  int top_error_count = 50;
  std::string sampling_mode = "ori_roundtrip";
};

struct CameraSample {
  int index;
  double sample;
  double line;
};

struct CameraPointRecord {
  int index;
  double input_sample;
  double input_line;
  double latitude;
  double longitude;
  double roundtrip_sample;
  double roundtrip_line;
};

struct RunningAbsStats {
  int count = 0;
  double total = 0.0;
  double total_sq = 0.0;
  double max_value = 0.0;

  void add(double value) {
    const double abs_value = std::abs(value);
    ++count;
    total += abs_value;
    total_sq += abs_value * abs_value;
    max_value = std::max(max_value, abs_value);
  }

  double mean() const {
    return count > 0 ? total / static_cast<double>(count) : 0.0;
  }

  double rms() const {
    return count > 0 ? std::sqrt(total_sq / static_cast<double>(count)) : 0.0;
  }
};

struct DomOriTopError {
  int index;
  double input_sample;
  double input_line;
  double dom_sample;
  double dom_line;
  double output_sample;
  double output_line;
  double sample_abs;
  double line_abs;
  double pixel_error;
};

double elapsed_seconds(std::chrono::steady_clock::time_point start) {
  return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
}

std::string qstring_to_string(const QString &value) {
  return value.toStdString();
}

std::string escape_json(const std::string &value) {
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (unsigned char ch : value) {
    switch (ch) {
      case '"':
        out << "\\\"";
        break;
      case '\\':
        out << "\\\\";
        break;
      case '\b':
        out << "\\b";
        break;
      case '\f':
        out << "\\f";
        break;
      case '\n':
        out << "\\n";
        break;
      case '\r':
        out << "\\r";
        break;
      case '\t':
        out << "\\t";
        break;
      default:
        if (ch < 0x20) {
          out << "\\u" << std::setw(4) << static_cast<int>(ch);
        } else {
          out << static_cast<char>(ch);
        }
        break;
    }
  }
  return out.str();
}

void require_value(int &index, int argc, char **argv, const std::string &flag) {
  if (index + 1 >= argc) {
    throw std::runtime_error(flag + " requires a value");
  }
}

int parse_positive_int(const std::string &value, const std::string &flag) {
  size_t parsed = 0;
  int result = std::stoi(value, &parsed);
  if (parsed != value.size() || result <= 0) {
    throw std::runtime_error(flag + " must be a positive integer");
  }
  return result;
}

Options parse_options(int argc, char **argv) {
  if (argc < 2) {
    throw std::runtime_error("usage: isis_cpp_benchmark <camera|controlnet|dom-ori|solar-geometry> [options]");
  }

  Options options;
  options.mode = argv[1];
  for (int i = 2; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "--label") {
      require_value(i, argc, argv, arg);
      options.label = argv[++i];
    } else if (arg == "--cube") {
      require_value(i, argc, argv, arg);
      options.cube_path = argv[++i];
    } else if (arg == "--dom") {
      require_value(i, argc, argv, arg);
      options.dom_path = argv[++i];
    } else if (arg == "--original") {
      require_value(i, argc, argv, arg);
      options.original_path = argv[++i];
    } else if (arg == "--net") {
      require_value(i, argc, argv, arg);
      options.net_path = argv[++i];
    } else if (arg == "--output") {
      require_value(i, argc, argv, arg);
      options.output_path = argv[++i];
    } else if (arg == "--sample-step") {
      require_value(i, argc, argv, arg);
      options.sample_step = parse_positive_int(argv[++i], arg);
    } else if (arg == "--line-step") {
      require_value(i, argc, argv, arg);
      options.line_step = parse_positive_int(argv[++i], arg);
    } else if (arg == "--max-points") {
      require_value(i, argc, argv, arg);
      options.max_points = parse_positive_int(argv[++i], arg);
    } else if (arg == "--point-count") {
      require_value(i, argc, argv, arg);
      options.point_count = parse_positive_int(argv[++i], arg);
    } else if (arg == "--top-error-count") {
      require_value(i, argc, argv, arg);
      options.top_error_count = parse_positive_int(argv[++i], arg);
    } else if (arg == "--sampling-mode") {
      require_value(i, argc, argv, arg);
      options.sampling_mode = argv[++i];
    } else {
      throw std::runtime_error("unknown argument: " + arg);
    }
  }

  if (options.mode != "camera" && options.mode != "controlnet" &&
      options.mode != "dom-ori" && options.mode != "solar-geometry") {
    throw std::runtime_error("mode must be camera, controlnet, dom-ori, or solar-geometry");
  }
  if (options.label.empty()) {
    throw std::runtime_error("--label is required");
  }
  if (options.output_path.empty()) {
    throw std::runtime_error("--output is required");
  }
  if (options.sampling_mode != "ori_roundtrip" && options.sampling_mode != "direct_dom") {
    throw std::runtime_error("--sampling-mode must be ori_roundtrip or direct_dom");
  }
  return options;
}

std::vector<double> linspace_axis(int count, int steps, const std::string &name) {
  if (count <= 0) {
    throw std::runtime_error(name + " count must be positive");
  }
  if (steps <= 0) {
    throw std::runtime_error(name + " steps must be positive");
  }
  if (steps == 1) {
    return {(static_cast<double>(count) + 1.0) / 2.0};
  }

  std::vector<double> values;
  values.reserve(static_cast<size_t>(steps));
  for (int index = 0; index < steps; ++index) {
    values.push_back(1.0 + (static_cast<double>(count) - 1.0) *
                            static_cast<double>(index) / static_cast<double>(steps - 1));
  }
  return values;
}

std::vector<CameraSample> generate_regular_grid_samples(
    int sample_count,
    int line_count,
    int point_count) {
  if (point_count <= 0) {
    throw std::runtime_error("point count must be positive");
  }
  const int columns = std::max(1, static_cast<int>(std::ceil(std::sqrt(static_cast<double>(point_count)))));
  const int rows = std::max(1, static_cast<int>(std::ceil(static_cast<double>(point_count) / columns)));
  const std::vector<double> sample_positions = linspace_axis(sample_count, columns, "sample");
  const std::vector<double> line_positions = linspace_axis(line_count, rows, "line");

  std::vector<CameraSample> samples;
  samples.reserve(static_cast<size_t>(point_count));
  for (double line : line_positions) {
    for (double sample : sample_positions) {
      samples.push_back(CameraSample{
          static_cast<int>(samples.size()),
          sample,
          line,
      });
      if (static_cast<int>(samples.size()) >= point_count) {
        return samples;
      }
    }
  }
  return samples;
}

std::vector<int> axis_positions(int count, int step, const std::string &name) {
  if (count <= 0) {
    throw std::runtime_error(name + " count must be positive");
  }
  if (step <= 0) {
    throw std::runtime_error(name + " step must be positive");
  }

  std::vector<int> positions;
  for (int position = 1; position <= count; position += step) {
    positions.push_back(position);
  }
  if (positions.back() != count) {
    positions.push_back(count);
  }
  return positions;
}

std::vector<CameraSample> generate_camera_samples(
    int sample_count,
    int line_count,
    int sample_step,
    int line_step,
    int max_points) {
  std::vector<CameraSample> samples;
  const std::vector<int> sample_positions = axis_positions(sample_count, sample_step, "sample");
  const std::vector<int> line_positions = axis_positions(line_count, line_step, "line");
  for (int line : line_positions) {
    for (int sample : sample_positions) {
      samples.push_back(CameraSample{
          static_cast<int>(samples.size()),
          static_cast<double>(sample),
          static_cast<double>(line),
      });
      if (max_points > 0 && static_cast<int>(samples.size()) >= max_points) {
        return samples;
      }
    }
  }
  return samples;
}

std::ofstream open_output(const std::string &path) {
  std::ofstream out(path);
  if (!out) {
    throw std::runtime_error("failed to open output path: " + path);
  }
  out << std::setprecision(17);
  return out;
}

void write_camera_result(const Options &options) {
  if (options.cube_path.empty()) {
    throw std::runtime_error("--cube is required for camera mode");
  }

  Isis::Cube cube;
  cube.open(QString::fromStdString(options.cube_path), "r");
  Isis::Camera *camera = cube.camera();
  const std::vector<CameraSample> samples = generate_camera_samples(
      camera->Samples(),
      camera->Lines(),
      options.sample_step,
      options.line_step,
      options.max_points);

  int failed_set_image_count = 0;
  int failed_set_universal_ground_count = 0;
  double core_seconds = 0.0;
  std::vector<CameraPointRecord> point_records;
  point_records.reserve(samples.size());

  for (const CameraSample &sample : samples) {
    const auto operation_start = std::chrono::steady_clock::now();
    if (!camera->SetImage(sample.sample, sample.line)) {
      core_seconds += elapsed_seconds(operation_start);
      ++failed_set_image_count;
      continue;
    }

    const double latitude = camera->UniversalLatitude();
    const double longitude = camera->UniversalLongitude();
    if (!camera->SetUniversalGround(latitude, longitude)) {
      core_seconds += elapsed_seconds(operation_start);
      ++failed_set_universal_ground_count;
      continue;
    }

    const double roundtrip_sample = camera->Sample();
    const double roundtrip_line = camera->Line();
    core_seconds += elapsed_seconds(operation_start);
    point_records.push_back(CameraPointRecord{
        sample.index,
        sample.sample,
        sample.line,
        latitude,
        longitude,
        roundtrip_sample,
        roundtrip_line,
    });
  }
  cube.close();

  std::ofstream out = open_output(options.output_path);
  out << "{\n"
      << "  \"task_type\": \"camera\",\n"
      << "  \"implementation\": \"cpp\",\n"
      << "  \"label\": \"" << escape_json(options.label) << "\",\n"
      << "  \"cube_path\": \"" << escape_json(options.cube_path) << "\",\n"
      << "  \"input_point_count\": " << samples.size() << ",\n"
      << "  \"successful_point_count\": " << point_records.size() << ",\n"
      << "  \"failed_set_image_count\": " << failed_set_image_count << ",\n"
      << "  \"failed_set_universal_ground_count\": " << failed_set_universal_ground_count << ",\n"
      << "  \"first_point_index\": ";
  if (samples.empty()) {
    out << "null";
  } else {
    out << samples.front().index;
  }
  out << ",\n"
      << "  \"core_seconds\": " << core_seconds << ",\n"
      << "  \"average_successful_point_seconds\": ";
  if (point_records.empty()) {
    out << "null";
  } else {
    out << core_seconds / static_cast<double>(point_records.size());
  }
  out << ",\n"
      << "  \"points\": [\n";
  for (size_t i = 0; i < point_records.size(); ++i) {
    const CameraPointRecord &point = point_records[i];
    if (i > 0) {
      out << ",\n";
    }
    out << "    {\"index\": " << point.index
        << ", \"input_sample\": " << point.input_sample
        << ", \"input_line\": " << point.input_line
        << ", \"latitude\": " << point.latitude
        << ", \"longitude\": " << point.longitude
        << ", \"roundtrip_sample\": " << point.roundtrip_sample
        << ", \"roundtrip_line\": " << point.roundtrip_line
        << "}";
  }
  out << "\n  ]\n"
      << "}\n";
}

void write_controlnet_result(const Options &options) {
  if (options.net_path.empty()) {
    throw std::runtime_error("--net is required for controlnet mode");
  }

  const auto load_start = std::chrono::steady_clock::now();
  Isis::ControlNet control_net(QString::fromStdString(options.net_path));
  const double load_seconds = elapsed_seconds(load_start);

  int measure_count = 0;
  std::map<std::string, int> serial_measure_counts;
  const auto traverse_start = std::chrono::steady_clock::now();
  const int point_count = control_net.GetNumPoints();
  for (int point_index = 0; point_index < point_count; ++point_index) {
    Isis::ControlPoint *point = control_net.GetPoint(point_index);
    (void)point->GetId();
    (void)point->GetPointTypeString();
    (void)point->IsIgnored();
    (void)point->IsEditLocked();

    const int point_measure_count = point->GetNumMeasures();
    for (int measure_index = 0; measure_index < point_measure_count; ++measure_index) {
      Isis::ControlMeasure *measure = point->GetMeasure(measure_index);
      ++measure_count;

      const std::string serial = qstring_to_string(measure->GetCubeSerialNumber());
      (void)measure->GetSample();
      (void)measure->GetLine();
      (void)measure->GetMeasureTypeString();
      (void)measure->IsIgnored();
      (void)measure->IsEditLocked();

      if (!serial.empty()) {
        serial_measure_counts[serial] += 1;
      }
    }
  }
  const double traverse_seconds = elapsed_seconds(traverse_start);

  const int valid_point_count = control_net.GetNumValidPoints();
  const int valid_measure_count = control_net.GetNumValidMeasures();
  const uintmax_t file_size_bytes = std::filesystem::exists(options.net_path)
      ? std::filesystem::file_size(options.net_path)
      : 0;
  const double measures_per_second = traverse_seconds > 0.0
      ? static_cast<double>(measure_count) / traverse_seconds
      : 0.0;

  std::ofstream out = open_output(options.output_path);
  out << "{\n"
      << "  \"task_type\": \"controlnet\",\n"
      << "  \"implementation\": \"cpp\",\n"
      << "  \"label\": \"" << escape_json(options.label) << "\",\n"
      << "  \"net_path\": \"" << escape_json(options.net_path) << "\",\n"
      << "  \"file_size_bytes\": " << file_size_bytes << ",\n"
      << "  \"point_count\": " << point_count << ",\n"
      << "  \"measure_count\": " << measure_count << ",\n"
      << "  \"valid_point_count\": " << valid_point_count << ",\n"
      << "  \"valid_measure_count\": " << valid_measure_count << ",\n"
      << "  \"serial_measure_counts\": {";
  bool first_serial = true;
  for (const auto &entry : serial_measure_counts) {
    if (!first_serial) {
      out << ", ";
    }
    first_serial = false;
    out << "\"" << escape_json(entry.first) << "\": " << entry.second;
  }
  out << "},\n"
      << "  \"load_seconds\": " << load_seconds << ",\n"
      << "  \"traverse_seconds\": " << traverse_seconds << ",\n"
      << "  \"core_seconds\": " << load_seconds + traverse_seconds << ",\n"
      << "  \"measures_per_second\": " << measures_per_second << "\n"
      << "}\n";
}

void write_dom_ori_direct_result(const Options &options) {
  if (options.dom_path.empty()) {
    throw std::runtime_error("--dom is required for dom-ori mode");
  }
  if (options.original_path.empty()) {
    throw std::runtime_error("--original is required for dom-ori mode");
  }

  Isis::Cube dom_cube;
  Isis::Cube original_cube;
  dom_cube.open(QString::fromStdString(options.dom_path), "r");
  original_cube.open(QString::fromStdString(options.original_path), "r");
  Isis::UniversalGroundMap dom_ground_map(dom_cube, Isis::UniversalGroundMap::ProjectionFirst);
  Isis::UniversalGroundMap original_ground_map(original_cube, Isis::UniversalGroundMap::CameraFirst);
  const std::vector<CameraSample> samples = generate_regular_grid_samples(
      dom_cube.sampleCount(),
      dom_cube.lineCount(),
      options.point_count);

  int failed_dom_lookup_count = 0;
  int failed_original_projection_count = 0;
  double core_seconds = 0.0;

  for (const CameraSample &sample : samples) {
    const auto operation_start = std::chrono::steady_clock::now();
    if (!dom_ground_map.SetImage(sample.sample, sample.line)) {
      core_seconds += elapsed_seconds(operation_start);
      ++failed_dom_lookup_count;
      continue;
    }
    const double latitude = dom_ground_map.UniversalLatitude();
    const double longitude = dom_ground_map.UniversalLongitude();
    if (!original_ground_map.SetUniversalGround(latitude, longitude)) {
      core_seconds += elapsed_seconds(operation_start);
      ++failed_original_projection_count;
      continue;
    }
    (void)original_ground_map.Sample();
    (void)original_ground_map.Line();
    core_seconds += elapsed_seconds(operation_start);
  }
  dom_cube.close();
  original_cube.close();

  const int failed_count = failed_dom_lookup_count + failed_original_projection_count;
  const int successful_point_count = options.point_count - failed_count;
  const double points_per_second = core_seconds > 0.0
      ? static_cast<double>(successful_point_count) / core_seconds
      : 0.0;

  std::ofstream out = open_output(options.output_path);
  out << "{\n"
      << "  \"task_type\": \"dom_ori\",\n"
      << "  \"implementation\": \"cpp\",\n"
      << "  \"label\": \"" << escape_json(options.label) << "\",\n"
      << "  \"sampling_mode\": \"direct_dom\",\n"
      << "  \"dom_path\": \"" << escape_json(options.dom_path) << "\",\n"
      << "  \"original_path\": \"" << escape_json(options.original_path) << "\",\n"
      << "  \"input_point_count\": " << options.point_count << ",\n"
      << "  \"successful_point_count\": " << successful_point_count << ",\n"
      << "  \"failed_count\": " << failed_count << ",\n"
      << "  \"failed_dom_lookup_count\": " << failed_dom_lookup_count << ",\n"
      << "  \"failed_original_projection_count\": " << failed_original_projection_count << ",\n"
      << "  \"core_seconds\": " << core_seconds << ",\n"
      << "  \"points_per_second\": " << points_per_second << ",\n"
      << "  \"sample_abs_max\": 0.0,\n"
      << "  \"sample_abs_mean\": 0.0,\n"
      << "  \"sample_abs_rms\": 0.0,\n"
      << "  \"line_abs_max\": 0.0,\n"
      << "  \"line_abs_mean\": 0.0,\n"
      << "  \"line_abs_rms\": 0.0,\n"
      << "  \"top_errors\": []\n"
      << "}\n";
}

void push_top_error(std::vector<DomOriTopError> &top_errors,
                    const DomOriTopError &row,
                    int limit) {
  if (limit <= 0) {
    return;
  }
  top_errors.push_back(row);
  std::sort(top_errors.begin(), top_errors.end(), [](const DomOriTopError &a, const DomOriTopError &b) {
    return a.pixel_error > b.pixel_error;
  });
  if (static_cast<int>(top_errors.size()) > limit) {
    top_errors.resize(static_cast<size_t>(limit));
  }
}

void write_dom_ori_top_errors(std::ofstream &out, const std::vector<DomOriTopError> &top_errors) {
  out << "  \"top_errors\": [\n";
  for (size_t i = 0; i < top_errors.size(); ++i) {
    const DomOriTopError &row = top_errors[i];
    if (i > 0) {
      out << ",\n";
    }
    out << "    {\"index\": " << row.index
        << ", \"input_sample\": " << row.input_sample
        << ", \"input_line\": " << row.input_line
        << ", \"dom_sample\": " << row.dom_sample
        << ", \"dom_line\": " << row.dom_line
        << ", \"output_sample\": " << row.output_sample
        << ", \"output_line\": " << row.output_line
        << ", \"sample_abs\": " << row.sample_abs
        << ", \"line_abs\": " << row.line_abs
        << ", \"pixel_error\": " << row.pixel_error
        << "}";
  }
  out << "\n  ]\n";
}

void write_dom_ori_roundtrip_result(const Options &options) {
  if (options.dom_path.empty()) {
    throw std::runtime_error("--dom is required for dom-ori mode");
  }
  if (options.original_path.empty()) {
    throw std::runtime_error("--original is required for dom-ori mode");
  }

  Isis::Cube dom_cube;
  Isis::Cube original_cube;
  dom_cube.open(QString::fromStdString(options.dom_path), "r");
  original_cube.open(QString::fromStdString(options.original_path), "r");
  Isis::Camera *original_camera = original_cube.camera();
  Isis::UniversalGroundMap dom_ground_map(dom_cube, Isis::UniversalGroundMap::ProjectionFirst);
  Isis::UniversalGroundMap original_ground_map(original_cube, Isis::UniversalGroundMap::CameraFirst);
  const std::vector<CameraSample> samples = generate_regular_grid_samples(
      original_cube.sampleCount(),
      original_cube.lineCount(),
      options.point_count);
  const int dom_sample_count = dom_cube.sampleCount();
  const int dom_line_count = dom_cube.lineCount();

  int failed_ori_set_image_count = 0;
  int failed_ori_ground_not_finite_count = 0;
  int failed_ori_to_dom_projection_count = 0;
  int failed_dom_point_out_of_bounds_count = 0;
  int failed_dom_lookup_count = 0;
  int failed_dom_to_ori_projection_count = 0;
  int ori_to_dom_successful_count = 0;
  int dom_ori_successful_count = 0;
  double ori_to_dom_seconds = 0.0;
  double dom_to_ori_seconds = 0.0;
  RunningAbsStats sample_stats;
  RunningAbsStats line_stats;
  RunningAbsStats pixel_error_stats;
  std::vector<DomOriTopError> top_errors;
  top_errors.reserve(static_cast<size_t>(std::min(options.top_error_count, options.point_count)));

  for (const CameraSample &sample : samples) {
    auto stage_start = std::chrono::steady_clock::now();
    if (!original_camera->SetImage(sample.sample, sample.line)) {
      ori_to_dom_seconds += elapsed_seconds(stage_start);
      ++failed_ori_set_image_count;
      continue;
    }

    const double latitude = original_camera->UniversalLatitude();
    const double longitude = original_camera->UniversalLongitude();
    if (!std::isfinite(latitude) || !std::isfinite(longitude)) {
      ori_to_dom_seconds += elapsed_seconds(stage_start);
      ++failed_ori_ground_not_finite_count;
      continue;
    }

    if (!dom_ground_map.SetUniversalGround(latitude, longitude)) {
      ori_to_dom_seconds += elapsed_seconds(stage_start);
      ++failed_ori_to_dom_projection_count;
      continue;
    }

    const double dom_sample = dom_ground_map.Sample();
    const double dom_line = dom_ground_map.Line();
    if (dom_sample < 1.0 || dom_sample > static_cast<double>(dom_sample_count) ||
        dom_line < 1.0 || dom_line > static_cast<double>(dom_line_count)) {
      ori_to_dom_seconds += elapsed_seconds(stage_start);
      ++failed_dom_point_out_of_bounds_count;
      continue;
    }
    ori_to_dom_seconds += elapsed_seconds(stage_start);
    ++ori_to_dom_successful_count;

    stage_start = std::chrono::steady_clock::now();
    if (!dom_ground_map.SetImage(dom_sample, dom_line)) {
      dom_to_ori_seconds += elapsed_seconds(stage_start);
      ++failed_dom_lookup_count;
      continue;
    }

    const double dom_latitude = dom_ground_map.UniversalLatitude();
    const double dom_longitude = dom_ground_map.UniversalLongitude();
    if (!original_ground_map.SetUniversalGround(dom_latitude, dom_longitude)) {
      dom_to_ori_seconds += elapsed_seconds(stage_start);
      ++failed_dom_to_ori_projection_count;
      continue;
    }

    const double output_sample = original_ground_map.Sample();
    const double output_line = original_ground_map.Line();
    dom_to_ori_seconds += elapsed_seconds(stage_start);
    ++dom_ori_successful_count;

    const double sample_error = output_sample - sample.sample;
    const double line_error = output_line - sample.line;
    const double pixel_error = std::hypot(sample_error, line_error);
    sample_stats.add(sample_error);
    line_stats.add(line_error);
    pixel_error_stats.add(pixel_error);
    push_top_error(top_errors,
                   DomOriTopError{
                       sample.index,
                       sample.sample,
                       sample.line,
                       dom_sample,
                       dom_line,
                       output_sample,
                       output_line,
                       std::abs(sample_error),
                       std::abs(line_error),
                       pixel_error,
                   },
                   options.top_error_count);
  }
  dom_cube.close();
  original_cube.close();

  const int ori_to_dom_failed_count = failed_ori_set_image_count +
                                      failed_ori_ground_not_finite_count +
                                      failed_ori_to_dom_projection_count +
                                      failed_dom_point_out_of_bounds_count;
  const int dom_ori_failed_count = failed_dom_lookup_count + failed_dom_to_ori_projection_count;
  const int failed_count = ori_to_dom_failed_count + dom_ori_failed_count;
  const double core_seconds = ori_to_dom_seconds + dom_to_ori_seconds;
  const double points_per_second = core_seconds > 0.0
      ? static_cast<double>(dom_ori_successful_count) / core_seconds
      : 0.0;
  const double roundtrip_success_rate = options.point_count > 0
      ? static_cast<double>(dom_ori_successful_count) / static_cast<double>(options.point_count)
      : 0.0;

  std::ofstream out = open_output(options.output_path);
  out << "{\n"
      << "  \"task_type\": \"dom_ori\",\n"
      << "  \"implementation\": \"cpp\",\n"
      << "  \"label\": \"" << escape_json(options.label) << "\",\n"
      << "  \"sampling_mode\": \"ori_roundtrip\",\n"
      << "  \"dom_path\": \"" << escape_json(options.dom_path) << "\",\n"
      << "  \"original_path\": \"" << escape_json(options.original_path) << "\",\n"
      << "  \"input_point_count\": " << options.point_count << ",\n"
      << "  \"ori_seed_point_count\": " << options.point_count << ",\n"
      << "  \"successful_point_count\": " << dom_ori_successful_count << ",\n"
      << "  \"roundtrip_successful_count\": " << dom_ori_successful_count << ",\n"
      << "  \"roundtrip_success_rate\": " << roundtrip_success_rate << ",\n"
      << "  \"failed_count\": " << failed_count << ",\n"
      << "  \"ori_to_dom_successful_count\": " << ori_to_dom_successful_count << ",\n"
      << "  \"ori_to_dom_failed_count\": " << ori_to_dom_failed_count << ",\n"
      << "  \"dom_ori_successful_count\": " << dom_ori_successful_count << ",\n"
      << "  \"dom_ori_failed_count\": " << dom_ori_failed_count << ",\n"
      << "  \"failed_ori_set_image_count\": " << failed_ori_set_image_count << ",\n"
      << "  \"failed_ori_ground_not_finite_count\": " << failed_ori_ground_not_finite_count << ",\n"
      << "  \"failed_ori_to_dom_projection_count\": " << failed_ori_to_dom_projection_count << ",\n"
      << "  \"failed_dom_point_out_of_bounds_count\": " << failed_dom_point_out_of_bounds_count << ",\n"
      << "  \"failed_dom_lookup_count\": " << failed_dom_lookup_count << ",\n"
      << "  \"failed_dom_to_ori_projection_count\": " << failed_dom_to_ori_projection_count << ",\n"
      << "  \"ori_to_dom_seconds\": " << ori_to_dom_seconds << ",\n"
      << "  \"dom_to_ori_seconds\": " << dom_to_ori_seconds << ",\n"
      << "  \"core_seconds\": " << core_seconds << ",\n"
      << "  \"points_per_second\": " << points_per_second << ",\n"
      << "  \"roundtrip_points_per_second\": " << points_per_second << ",\n"
      << "  \"sample_abs_max\": " << sample_stats.max_value << ",\n"
      << "  \"sample_abs_mean\": " << sample_stats.mean() << ",\n"
      << "  \"sample_abs_rms\": " << sample_stats.rms() << ",\n"
      << "  \"line_abs_max\": " << line_stats.max_value << ",\n"
      << "  \"line_abs_mean\": " << line_stats.mean() << ",\n"
      << "  \"line_abs_rms\": " << line_stats.rms() << ",\n"
      << "  \"pixel_error_abs_max\": " << pixel_error_stats.max_value << ",\n"
      << "  \"pixel_error_abs_mean\": " << pixel_error_stats.mean() << ",\n"
      << "  \"pixel_error_abs_rms\": " << pixel_error_stats.rms() << ",\n";
  write_dom_ori_top_errors(out, top_errors);
  out << "}\n";
}

void write_dom_ori_result(const Options &options) {
  if (options.sampling_mode == "direct_dom") {
    write_dom_ori_direct_result(options);
  } else {
    write_dom_ori_roundtrip_result(options);
  }
}

void write_solar_geometry_result(const Options &options) {
  if (options.cube_path.empty()) {
    throw std::runtime_error("--cube is required for solar-geometry mode");
  }

  Isis::Cube cube;
  cube.open(QString::fromStdString(options.cube_path), "r");
  Isis::Camera *camera = cube.camera();
  const std::vector<CameraSample> samples = generate_regular_grid_samples(
      cube.sampleCount(),
      cube.lineCount(),
      options.point_count);

  int failed_set_image_count = 0;
  double core_seconds = 0.0;
  for (const CameraSample &sample : samples) {
    const auto operation_start = std::chrono::steady_clock::now();
    if (!camera->SetImage(sample.sample, sample.line)) {
      core_seconds += elapsed_seconds(operation_start);
      ++failed_set_image_count;
      continue;
    }
    (void)camera->SunAzimuth();
    (void)(90.0 - camera->IncidenceAngle());
    core_seconds += elapsed_seconds(operation_start);
  }
  cube.close();

  const int successful_point_count = options.point_count - failed_set_image_count;
  const double points_per_second = core_seconds > 0.0
      ? static_cast<double>(successful_point_count) / core_seconds
      : 0.0;

  std::ofstream out = open_output(options.output_path);
  out << "{\n"
      << "  \"task_type\": \"solar_geometry\",\n"
      << "  \"implementation\": \"cpp\",\n"
      << "  \"label\": \"" << escape_json(options.label) << "\",\n"
      << "  \"cube_path\": \"" << escape_json(options.cube_path) << "\",\n"
      << "  \"input_point_count\": " << options.point_count << ",\n"
      << "  \"successful_point_count\": " << successful_point_count << ",\n"
      << "  \"failed_count\": " << failed_set_image_count << ",\n"
      << "  \"failed_set_image_count\": " << failed_set_image_count << ",\n"
      << "  \"core_seconds\": " << core_seconds << ",\n"
      << "  \"points_per_second\": " << points_per_second << ",\n"
      << "  \"azimuth_abs_max\": 0.0,\n"
      << "  \"azimuth_abs_mean\": 0.0,\n"
      << "  \"azimuth_abs_rms\": 0.0,\n"
      << "  \"elevation_abs_max\": 0.0,\n"
      << "  \"elevation_abs_mean\": 0.0,\n"
      << "  \"elevation_abs_rms\": 0.0,\n"
      << "  \"top_errors\": []\n"
      << "}\n";
}

}  // namespace

int main(int argc, char **argv) {
  try {
    const Options options = parse_options(argc, argv);
    if (options.mode == "camera") {
      write_camera_result(options);
    } else if (options.mode == "controlnet") {
      write_controlnet_result(options);
    } else if (options.mode == "dom-ori") {
      write_dom_ori_result(options);
    } else {
      write_solar_geometry_result(options);
    }
    return EXIT_SUCCESS;
  } catch (const Isis::IException &error) {
    std::cerr << error.toString().toStdString() << std::endl;
  } catch (const std::exception &error) {
    std::cerr << error.what() << std::endl;
  }
  return EXIT_FAILURE;
}
