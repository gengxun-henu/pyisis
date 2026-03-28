#ifndef PointCloudTree_h
#define PointCloudTree_h

/** This is free and unencumbered software released into the public domain.

The authors of ISIS do not claim copyright on the contents of this file.
For more details about the LICENSE terms and the AUTHORS, you will
find files of those names at the top level of this repository. **/

/* SPDX-License-Identifier: CC0-1.0 */

#include <cstdlib>
#include <utility>
#include <vector>

#include <QList>
#include <QSharedPointer>
#include <QVector>

#include <nanoflann.hpp>

#include "PointCloud.h"

namespace Isis {

#if NANOFLANN_VERSION >= 0x160
typedef nanoflann::SearchParameters NanoflannSearchParams;
#else
typedef nanoflann::SearchParams NanoflannSearchParams;
#endif

/**
 * @brief Point cloud kd-tree class using the nanoflann kd-tree library
 *
 * This class renders a point cloud in a kd-tree for very fast/efficient point
 * queries. This implementation is specifically used by cnetcombinept for
 * image-space MeasurePoint lookups.
 *
 * @author 2014-02-17 Kris Becker
 *
 * @internal
 *   @history 2014-02-17 Kris Becker - Original Version
 *   @history 2026-03-14 GitHub Copilot - Restored header after an accidental
 *            copy/paste from cnet2dem introduced duplicate guards and the
 *            wrong template/query API for cnetcombinept.
 */
template <class T>
class PointCloudTree {
  private:
    typedef nanoflann::KDTreeSingleIndexAdaptor<
                        nanoflann::L2_Simple_Adaptor<double, PointCloud<T> >,
                        PointCloud<T>, Dist2d<T>::Dimension> PcKdTree_t;

  public:
    /**
     * @brief Constructor of PointCloudTree for the kd-tree point representation
     *
     * @param pc        Pointer to PointCloud to build the kd-tree from. This
     *                  object takes complete ownership of the PointCloud pointer.
     * @param leafNodes Maximum number of leaves stored at each kd-tree node.
     */
    PointCloudTree(PointCloud<T> *pc, const int &leafNodes = 10) : m_pc(pc),
      m_kd_index(Dist2d<T>::Dimension, *pc,
                 nanoflann::KDTreeSingleIndexAdaptorParams(leafNodes)) {
      m_kd_index.buildIndex();
    }

    /** Destructor */
    virtual ~PointCloudTree() { }

    /** Perform radius query in squared image-space units. */
    QList<T> radius_query(const T &point, const double &radius_sq) const {
      QList<T> results;

#if NANOFLANN_VERSION >= 0x160
      std::vector<nanoflann::ResultItem<typename PcKdTree_t::IndexType, double> > matches;
      m_kd_index.radiusSearch(point.array(), radius_sq, matches,
                              NanoflannSearchParams());
      for (size_t i = 0; i < matches.size(); i++) {
        results.append(m_pc->point(static_cast<size_t>(matches[i].first)));
      }
#else
      std::vector<std::pair<size_t, double> > matches;
      m_kd_index.radiusSearch(point.array(), radius_sq, matches,
                              NanoflannSearchParams());
      for (size_t i = 0; i < matches.size(); i++) {
        results.append(m_pc->point(matches[i].first));
      }
#endif

      return results;
    }

    /** Perform nearest-neighbor query. */
    QList<T> neighbor_query(const T &point, const int &neighbors) const {
      QVector<typename PcKdTree_t::IndexType> kd_indices(neighbors);
      QVector<double> distances(neighbors);
      QList<T> results;

      m_kd_index.knnSearch(point.array(), neighbors, kd_indices.data(),
                           distances.data());

      for (int i = 0; i < neighbors; i++) {
        results.append(m_pc->point(static_cast<size_t>(kd_indices[i])));
      }

      return results;
    }

    /** Returns a reference to the point cloud. */
    inline const PointCloud<T> &cloud() const {
      return (*m_pc);
    }

  private:
    QSharedPointer<PointCloud<T> > m_pc;
    PcKdTree_t                     m_kd_index;
};

}  // namespace Isis
#endif
