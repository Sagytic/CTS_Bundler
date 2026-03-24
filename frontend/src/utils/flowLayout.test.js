import { describe, it, expect } from 'vitest';
import { keepConnectedToRoot } from './flowLayout';

describe('flowLayout', () => {
  describe('keepConnectedToRoot', () => {
    it('returns empty nodes and edges when nodes array is empty', () => {
      const result = keepConnectedToRoot([], [], 'root');
      expect(result).toEqual({ nodes: [], edges: [] });
    });

    it('returns only the root node when there are no edges', () => {
      const nodes = [{ id: 'n1' }, { id: 'n2' }];
      const edges = [];
      const result = keepConnectedToRoot(nodes, edges, 'n1');
      expect(result).toEqual({
        nodes: [{ id: 'n1' }],
        edges: []
      });
    });

    it('returns all nodes and edges for a fully connected graph', () => {
      const nodes = [{ id: 'n1' }, { id: 'n2' }, { id: 'n3' }];
      const edges = [
        { source: 'n1', target: 'n2' },
        { source: 'n2', target: 'n3' }
      ];
      const result = keepConnectedToRoot(nodes, edges, 'n1');
      expect(result).toEqual({
        nodes,
        edges
      });
    });

    it('removes disconnected nodes and their edges', () => {
      const nodes = [{ id: 'n1' }, { id: 'n2' }, { id: 'n3' }, { id: 'n4' }];
      const edges = [
        { source: 'n1', target: 'n2' },
        { source: 'n3', target: 'n4' } // Disconnected from n1
      ];
      const result = keepConnectedToRoot(nodes, edges, 'n1');
      expect(result).toEqual({
        nodes: [{ id: 'n1' }, { id: 'n2' }],
        edges: [{ source: 'n1', target: 'n2' }]
      });
    });

    it('uses the first node as root if rootId is not found in nodes', () => {
      const nodes = [{ id: 'n1' }, { id: 'n2' }];
      const edges = [{ source: 'n1', target: 'n2' }];
      const result = keepConnectedToRoot(nodes, edges, 'missing-root');
      expect(result).toEqual({
        nodes,
        edges
      });
    });

    it('handles cyclic graphs without getting stuck', () => {
      const nodes = [{ id: 'n1' }, { id: 'n2' }, { id: 'n3' }];
      const edges = [
        { source: 'n1', target: 'n2' },
        { source: 'n2', target: 'n3' },
        { source: 'n3', target: 'n1' } // Cycle
      ];
      const result = keepConnectedToRoot(nodes, edges, 'n1');
      expect(result).toEqual({
        nodes,
        edges
      });
    });

    it('handles multiple edges to the same node', () => {
      const nodes = [{ id: 'n1' }, { id: 'n2' }];
      const edges = [
        { source: 'n1', target: 'n2' },
        { source: 'n2', target: 'n1' }
      ];
      const result = keepConnectedToRoot(nodes, edges, 'n1');
      expect(result).toEqual({
        nodes,
        edges
      });
    });

    it('ignores edges referencing non-existent nodes', () => {
      const nodes = [{ id: 'n1' }, { id: 'n2' }];
      const edges = [
        { source: 'n1', target: 'n2' },
        { source: 'n2', target: 'n3' } // n3 doesn't exist
      ];
      const result = keepConnectedToRoot(nodes, edges, 'n1');
      expect(result).toEqual({
        nodes,
        edges: [{ source: 'n1', target: 'n2' }] // Only the valid edge should be kept
      });
    });
  });
});
